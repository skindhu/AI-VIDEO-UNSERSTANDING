"""
字幕处理模块：处理、过滤和合并视频字幕
"""

import os
import json
import logging
from difflib import SequenceMatcher

from . import config # 导入配置模块

class SubtitleProcessor:
    """字幕处理器：处理、过滤和合并视频字幕"""

    def __init__(self, transcript_path=None):
        """
        初始化字幕处理器

        Args:
            transcript_path (str, optional): 语音识别文件路径，默认为None
        """
        self.logger = logging.getLogger("SubtitleProcessor")
        self.segments = []
        self.output_frame_rate = 0  # 会在处理时从config获取

        # 如果提供了转录文件路径，则加载时间分段信息
        if transcript_path and os.path.exists(transcript_path):
            self.load_transcript(transcript_path)

    def load_transcript(self, transcript_path):
        """
        加载语音识别转录文件，提取时间分段信息

        Args:
            transcript_path (str): 转录文件路径
        """
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)

            # 提取时间分段信息
            if 'segments' in transcript_data:
                self.segments = transcript_data['segments']
                self.logger.info(f"已加载 {len(self.segments)} 个时间分段")
            else:
                self.logger.warning("转录文件中未找到segments字段")

        except Exception as e:
            self.logger.error(f"加载转录文件失败: {str(e)}")
            self.segments = []

    def get_segment_by_time(self, timestamp):
        """
        根据时间戳获取对应的分段

        Args:
            timestamp (float): 时间戳（秒）

        Returns:
            dict: 对应的分段，如果未找到则返回None
        """
        if not self.segments:
            return None

        for segment in self.segments:
            if 'start' in segment and 'end' in segment:
                if segment['start'] <= timestamp <= segment['end']:
                    return segment

        return None

    def frame_to_timestamp(self, frame_number):
        """
        将帧号转换为时间戳 (基于输出帧率)
        时间戳代表该帧对应时间区间的起始点。

        Args:
            frame_number (int): 帧号

        Returns:
            float: 时间戳（秒）
        """
        if not self.output_frame_rate or self.output_frame_rate <= 0:
            # 尝试从config获取
            if config.OUTPUT_FRAME_RATE and config.OUTPUT_FRAME_RATE > 0:
                 self.output_frame_rate = config.OUTPUT_FRAME_RATE
            else:
                self.logger.error("输出帧率(OUTPUT_FRAME_RATE)未在config中设置，无法转换帧号到时间戳")
                raise ValueError("无法获取有效的输出帧率")

        # 修正：(帧号 - 1) / 帧率 得到起始时间戳
        return (frame_number - 1) / self.output_frame_rate

    def extract_frame_number(self, frame_filename):
        """
        从帧文件名中提取帧号

        Args:
            frame_filename (str): 帧文件名，格式如frame_000001.png

        Returns:
            int: 帧号
        """
        try:
            # 尝试提取数字部分
            if '_' in frame_filename:
                # 假设格式为frame_000001.png
                num_part = frame_filename.split('_')[1].split('.')[0]
                return int(num_part)
            else:
                # 尝试其他可能的格式
                base_name = os.path.splitext(frame_filename)[0]
                # 提取数字部分
                digits = ''.join(filter(str.isdigit, base_name))
                return int(digits) if digits else 0
        except Exception as e:
            self.logger.error(f"从文件名提取帧号失败: {str(e)}")
            return 0

    def is_similar_text(self, text1, text2, threshold=0.95):
        """
        判断两段文本是否相似

        Args:
            text1 (str): 第一段文本
            text2 (str): 第二段文本
            threshold (float, optional): 相似度阈值，默认为0.85

        Returns:
            bool: 如果相似度高于阈值则返回True
        """
        if text1 == text2:
            return True

        if not text1 or not text2:
            return False

        # 使用SequenceMatcher计算相似度
        similarity = SequenceMatcher(None, text1, text2).ratio()
        return similarity >= threshold

    def process_subtitles(self, subtitle_results, output_path=None, similarity_threshold=0.85):
        """
        处理字幕结果，过滤重复内容并按时间戳合并

        Args:
            subtitle_results (list): 字幕提取结果列表，每项包含frame_name和subtitle
            output_path (str, optional): 结果输出路径，默认为None
            similarity_threshold (float, optional): 字幕相似度阈值，默认为0.85

        Returns:
            list: 处理后的字幕列表，每项包含text, start_time, end_time
        """
        # 从config获取输出帧率
        self.output_frame_rate = config.OUTPUT_FRAME_RATE
        if not self.output_frame_rate or self.output_frame_rate <= 0:
            self.logger.error("输出帧率(OUTPUT_FRAME_RATE)未在config中设置，无法处理字幕")
            raise ValueError("无法获取有效的输出帧率以处理字幕")

        processed_subtitles = []
        current_subtitle = None

        # 对结果按帧文件名排序
        subtitle_results.sort(key=lambda x: self.extract_frame_number(x['frame_name']))

        for result in subtitle_results:
            frame_name = result['frame_name']
            subtitle_text = result['subtitle']

            # 忽略处理失败或无字幕的情况
            if subtitle_text == '分析失败' or subtitle_text == '无字幕':
                continue

            # 提取帧号并转换为时间戳
            try:
                frame_number = self.extract_frame_number(frame_name)
                timestamp = self.frame_to_timestamp(frame_number)
            except ValueError as e:
                self.logger.warning(f"无法为帧 {frame_name} 计算时间戳: {e}. 跳过此帧.")
                continue

            # 如果是第一条字幕，直接添加
            if current_subtitle is None:
                current_subtitle = {
                    'text': subtitle_text,
                    'start_time': timestamp,
                    'end_time': timestamp,
                    'frame_start': frame_number,
                    'frame_end': frame_number
                }
                continue

            # 检查当前字幕是否与前一条相似
            if self.is_similar_text(subtitle_text, current_subtitle['text'], similarity_threshold):
                # 更新结束时间
                current_subtitle['end_time'] = timestamp
                current_subtitle['frame_end'] = frame_number
            else:
                # 添加前一条字幕到结果列表
                processed_subtitles.append(current_subtitle)
                # 创建新的当前字幕
                current_subtitle = {
                    'text': subtitle_text,
                    'start_time': timestamp,
                    'end_time': timestamp,
                    'frame_start': frame_number,
                    'frame_end': frame_number
                }

        # 添加最后一条字幕
        if current_subtitle:
            processed_subtitles.append(current_subtitle)

        # 根据语音识别分段调整字幕时间（如果有）
        if self.segments:
            self.adjust_subtitles_with_segments(processed_subtitles)

        # 移除不需要的字段
        for subtitle in processed_subtitles:
            if 'frame_start' in subtitle:
                del subtitle['frame_start']
            if 'frame_end' in subtitle:
                del subtitle['frame_end']

        # 保存结果（如果指定了输出路径）
        if output_path:
            try:
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'subtitles': processed_subtitles,
                        'output_frame_rate': self.output_frame_rate # 保存处理时使用的帧率
                    }, f, ensure_ascii=False, indent=2)
                self.logger.info(f"处理后的字幕已保存到 {output_path}")
            except Exception as e:
                self.logger.error(f"保存处理后的字幕失败: {str(e)}")

        return processed_subtitles

    def adjust_subtitles_with_segments(self, subtitles):
        """
        根据语音识别分段调整字幕时间

        Args:
            subtitles (list): 字幕列表
        """
        if not self.segments or not subtitles:
            return

        for subtitle in subtitles:
            # 查找字幕中间点对应的分段
            mid_time = (subtitle['start_time'] + subtitle['end_time']) / 2
            segment = self.get_segment_by_time(mid_time)

            if segment and 'start' in segment and 'end' in segment:
                # 判断是否需要调整
                # 仅当分段边界与字幕边界相差较大时才调整
                if abs(segment['start'] - subtitle['start_time']) > 0.5:
                    subtitle['start_time'] = segment['start']
                if abs(segment['end'] - subtitle['end_time']) > 0.5:
                    subtitle['end_time'] = segment['end']

    def export_to_srt(self, subtitles, output_path):
        """
        将字幕导出为SRT格式

        Args:
            subtitles (list): 字幕列表
            output_path (str): 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, subtitle in enumerate(subtitles):
                    # 序号
                    f.write(f"{i+1}\n")

                    # 时间码（格式：00:00:00,000 --> 00:00:00,000）
                    start_time = self.format_time_for_srt(subtitle['start_time'])
                    end_time = self.format_time_for_srt(subtitle['end_time'])
                    f.write(f"{start_time} --> {end_time}\n")

                    # 字幕文本
                    f.write(f"{subtitle['text']}\n\n")

            self.logger.info(f"字幕已成功导出为SRT格式: {output_path}")
        except Exception as e:
            self.logger.error(f"导出SRT字幕失败: {str(e)}")

    def format_time_for_srt(self, seconds):
        """
        将秒数格式化为SRT时间格式

        Args:
            seconds (float): 秒数

        Returns:
            str: SRT格式的时间（00:00:00,000）
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)

        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"