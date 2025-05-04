"""
视觉内容提取模块：调用AI服务分析视频帧内容
"""

import os
import json
import logging
import time
import concurrent.futures # 引入并发库
from tqdm import tqdm

from .subtitle_processor import SubtitleProcessor
from . import config # 导入配置模块

class VisualExtractor:
    """视觉内容提取器，分析视频帧中的内容"""

    def __init__(self, ai_service):
        """
        初始化视觉内容提取器

        Args:
            ai_service: AI服务接口
        """
        self.ai_service = ai_service
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("VisualExtractor")

    def analyze_frame(self, frame_path):
        """
        分析单个视频帧 (调用AI服务)

        Args:
            frame_path (str): 帧图像路径

        Returns:
            dict: 分析结果，包含帧文件名和提取的字幕
        """
        try:
            if not os.path.exists(frame_path):
                raise FileNotFoundError(f"帧图像不存在: {frame_path}")

            # 提取字幕
            subtitle = self.ai_service.describe_image(frame_path)

            # 返回结果
            frame_name = os.path.basename(frame_path)
            return {
                "frame_name": frame_name,
                "subtitle": subtitle
            }
        except Exception as e:
            self.logger.error(f"分析帧 {frame_path} 失败: {str(e)}")
            return {
                "frame_name": os.path.basename(frame_path),
                "subtitle": "分析失败",
                "error": str(e)
            }

    def _analyze_frame_task(self, frame_number, frame_path):
        """多线程执行的单个帧分析任务"""
        try:
            self.logger.info(f"开始分析帧 {frame_path} (编号 {frame_number})")
            analysis_result = self.analyze_frame(frame_path)
            # 将原始帧号添加到结果中，用于后续排序
            analysis_result['frame_number'] = frame_number
            return {'status': 'success', 'data': analysis_result}
        except Exception as e:
            # analyze_frame内部已经处理了大部分异常并返回字典
            # 此处的except主要捕获analyze_frame调用本身可能出现的意外错误
            self.logger.error(f"执行分析任务时捕获意外错误 (帧 {frame_path}): {e}")
            return {'status': 'error', 'frame_number': frame_number, 'path': frame_path, 'error': str(e)}

    def _load_transcript_segments(self, transcript_path):
        """
        辅助函数：加载并返回语音识别转录文件中的时间分段信息
        """
        segments = []
        if transcript_path and os.path.exists(transcript_path):
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                if 'segments' in transcript_data:
                    segments = transcript_data['segments']
                    self.logger.info(f"从 {transcript_path} 加载了 {len(segments)} 个时间分段")
                else:
                    self.logger.warning(f"转录文件 {transcript_path} 中未找到segments字段")
            except Exception as e:
                self.logger.error(f"加载转录文件 {transcript_path} 失败: {str(e)}")
        else:
            self.logger.warning("未提供有效的转录文件路径，无法使用时间戳优化")
        return segments

    def _find_segment_for_timestamp(self, timestamp, segments):
        """
        辅助函数：根据时间戳查找对应的分段
        """
        if not segments:
            return None
        for segment in segments:
            if 'start' in segment and 'end' in segment:
                # 允许一点点误差，以防时间戳正好落在边界外一点点
                if segment['start'] - 0.1 <= timestamp <= segment['end'] + 0.1:
                    return segment
        return None

    def _frame_to_timestamp(self, frame_number):
        """
        辅助函数：将帧号转换为时间戳，依赖于config.OUTPUT_FRAME_RATE
        时间戳代表该帧对应时间区间的起始点。
        """
        frame_rate = config.OUTPUT_FRAME_RATE
        if not frame_rate or frame_rate <= 0:
            self.logger.error("输出帧率未在config中设置或无效，无法转换帧号到时间戳")
            raise ValueError("无法获取有效的输出帧率")
        # 修正：(帧号 - 1) / 帧率 得到起始时间戳
        return (frame_number - 1) / frame_rate

    def _extract_frame_number(self, frame_filename):
        """
        辅助函数：从帧文件名中提取帧号
        """
        try:
            if '_' in frame_filename:
                num_part = frame_filename.split('_')[1].split('.')[0]
                return int(num_part)
            else:
                base_name = os.path.splitext(frame_filename)[0]
                digits = ''.join(filter(str.isdigit, base_name))
                return int(digits) if digits else 0
        except Exception as e:
            self.logger.error(f"从文件名 {frame_filename} 提取帧号失败: {str(e)}")
            return 0 # 返回0或其他默认值，或抛出异常

    def analyze_batch(self, frames_dir, output_path=None, similarity_threshold=config.SUBTITLE_MERGE_THRESHOLD_SIMILARITY,
                      silent_sample_interval=1.0, segment_sample_interval=2.0):
        """
        批量分析视频帧并处理字幕 (基于时间戳智能选择帧, 使用多线程分析)

        Args:
            frames_dir (str): 帧图像目录路径
            output_path (str, optional): 结果输出路径 (JSON格式)。
            similarity_threshold (float, optional): 字幕相似度阈值，用于SubtitleProcessor合并。
            silent_sample_interval (float, optional): 静音段（无语音分段）的采样间隔（秒）。
            segment_sample_interval (float, optional): 语音分段内部的采样间隔（秒）。设为0或负数则只分析边界。

        Returns:
            list: 处理后的字幕列表 (由SubtitleProcessor返回)
        """
        start_time_batch = time.time()
        self.logger.info(f"开始优化批量分析 (多线程): {frames_dir}")
        if not os.path.exists(frames_dir):
            raise FileNotFoundError(f"帧图像目录不存在: {frames_dir}")

        # 检查帧率
        if not config.OUTPUT_FRAME_RATE or config.OUTPUT_FRAME_RATE <= 0:
            self.logger.error("视频输出帧率未在config中设置，无法执行基于时间的优化。")
            # 可以选择回退到原始的 analyze_batch 逻辑，或者直接抛出错误
            raise ValueError("视频输出帧率未设置，无法执行 analyze_batch")
        transcript_path = config.TRANSCRIPT_PATH
        # 加载时间分段信息
        segments = self._load_transcript_segments(transcript_path)

        # 获取并排序所有有效的帧文件
        valid_extensions = ['.jpg', '.jpeg', '.png']
        all_frame_paths = []
        for file in os.listdir(frames_dir):
            file_path = os.path.join(frames_dir, file)
            if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in valid_extensions):
                all_frame_paths.append(file_path)
        if not all_frame_paths:
            raise ValueError(f"在目录 {frames_dir} 中未找到有效的帧图像")
        all_frame_paths.sort(key=lambda x: self._extract_frame_number(os.path.basename(x)))
        self.logger.info(f"找到 {len(all_frame_paths)} 个有效帧图像")

        # --- 2. 顺序帧选择 ---
        frames_to_analyze_list = [] # 存储 (frame_number, frame_path) 元组
        last_analyzed_timestamp = -1.0
        last_analyzed_segment = None
        selected_frames_count = 0

        self.logger.info(f"开始智能帧选择 (静音间隔: {silent_sample_interval}s, 语音段间隔: {segment_sample_interval}s)")
        start_time_selection = time.time()
        for current_frame_path in all_frame_paths: # 不使用tqdm，避免日志冲突
            try:
                current_frame_number = self._extract_frame_number(os.path.basename(current_frame_path))
                if current_frame_number == 0: # 跳过无法提取帧号的文件
                     self.logger.warning(f"无法从 {os.path.basename(current_frame_path)} 提取有效帧号，跳过此帧。")
                     continue
                current_timestamp = self._frame_to_timestamp(current_frame_number)
            except ValueError as e:
                self.logger.warning(f"无法计算帧 {current_frame_path} 的时间戳: {e}. 跳过此帧.")
                continue
            except Exception as e:
                self.logger.warning(f"处理帧文件名 {current_frame_path} 出错: {e}. 跳过此帧.")
                continue

            current_segment = self._find_segment_for_timestamp(current_timestamp, segments)
            should_analyze = False

            # 决策逻辑：
            # a) 总是分析第一帧
            if last_analyzed_timestamp < 0:
                should_analyze = True
                self.logger.info(f"[分析决策] 分析第一帧: {os.path.basename(current_frame_path)}")
            else:
                # b) 分析语音段边界 (进入或离开一个segment)
                if current_segment != last_analyzed_segment:
                    should_analyze = True
                    reason = "进入新分段" if current_segment else "离开分段进入静音"
                    if last_analyzed_segment is None and current_segment is not None:
                         reason = "从静音进入分段"
                    self.logger.info(f"[分析决策] {reason} ({current_segment.get('text', 'N/A') if current_segment else '静音'} @ {current_timestamp:.2f}s): 分析帧 {os.path.basename(current_frame_path)}")
                else:
                    # c) 如果在静音段，按间隔采样
                    if current_segment is None:
                        time_diff = current_timestamp - last_analyzed_timestamp
                        if time_diff >= silent_sample_interval:
                            should_analyze = True
                            self.logger.info(f"[分析决策] 静音段采样 (间隔 {time_diff:.2f}s >= {silent_sample_interval}s): 分析帧 {os.path.basename(current_frame_path)}")
                    # d) 如果在语音段内部，按间隔采样 (如果间隔 > 0)
                    elif segment_sample_interval > 0:
                        time_diff = current_timestamp - last_analyzed_timestamp
                        if time_diff >= segment_sample_interval:
                            should_analyze = True
                            self.logger.info(f"[分析决策] 语音段采样 (间隔 {time_diff:.2f}s >= {segment_sample_interval}s): 分析帧 {os.path.basename(current_frame_path)}")

            # 添加到待分析列表，并更新状态
            if should_analyze:
                frames_to_analyze_list.append((current_frame_number, current_frame_path))
                selected_frames_count += 1
                last_analyzed_timestamp = current_timestamp
                last_analyzed_segment = current_segment

        selection_duration = time.time() - start_time_selection
        self.logger.info(f"智能帧选择完成，耗时 {selection_duration:.2f} 秒，选择了 {selected_frames_count} / {len(all_frame_paths)} 帧进行分析")

        # --- 3. 并行帧分析 ---
        results_for_processor = [] # 存储排序后的成功分析结果
        if not frames_to_analyze_list:
            self.logger.warning("没有帧被选择进行分析。")
        else:
            self.logger.info(f"开始使用最多 {config.VISUAL_EXTRACTION_MAX_WORKERS} 个线程并行分析 {len(frames_to_analyze_list)} 帧...")
            start_time_analysis = time.time()
            raw_thread_results = []
            futures = {} # 用于存储 future 到 (frame_num, frame_path) 的映射

            with concurrent.futures.ThreadPoolExecutor(max_workers=config.VISUAL_EXTRACTION_MAX_WORKERS) as executor:
                # 提交任务
                for frame_num, frame_path in frames_to_analyze_list:
                     future = executor.submit(self._analyze_frame_task, frame_num, frame_path)
                     futures[future] = (frame_num, frame_path)

                # 使用tqdm显示进度
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="并行分析帧"):
                    frame_num, frame_path = futures[future]
                    try:
                        result = future.result()
                        raw_thread_results.append(result)
                    except Exception as exc:
                        # 通常 _analyze_frame_task 内部会处理异常并返回字典
                        # 这里的捕获是额外的保险
                        self.logger.error(f'帧 {frame_path} (编号 {frame_num}) 在future执行中产生意外异常: {exc}')
                        raw_thread_results.append({'status': 'error', 'frame_number': frame_num, 'path': frame_path, 'error': str(exc)})

            analysis_duration = time.time() - start_time_analysis
            self.logger.info(f"并行分析完成，耗时 {analysis_duration:.2f} 秒")

            # --- 4. 结果处理与排序 ---
            # 提取成功的结果并排序
            successful_results_with_num = [res['data'] for res in raw_thread_results if res['status'] == 'success' and 'data' in res]
            successful_results_with_num.sort(key=lambda x: x.get('frame_number', 0)) # 按帧号排序

            # 移除frame_number字段，得到最终用于processor的列表
            results_for_processor = []
            for res in successful_results_with_num:
                proc_res = {k: v for k, v in res.items() if k != 'frame_number'}
                results_for_processor.append(proc_res)

            # 记录错误
            errors = [res for res in raw_thread_results if res['status'] == 'error']
            if errors:
                self.logger.warning(f"并行分析过程中遇到 {len(errors)} 个错误。")
                # for err in errors[:5]: # 最多记录前5个错误详情
                #     self.logger.debug(f"  - 帧 {err.get('path', '?')} (编号 {err.get('frame_number', '?')}): {err.get('error', '?')}")

            self.logger.info(f"成功分析并排序了 {len(results_for_processor)} 帧的结果")

        # --- 5. 保存原始结果 (排序后的成功结果) ---
        if output_path is None:
            output_dir = os.path.join(config.OUTPUT_DIR, 'subtitles')
            os.makedirs(output_dir, exist_ok=True)
            # base_name = os.path.basename(os.path.normpath(frames_dir))
            output_path = os.path.join(output_dir, f'{config.VIDEO_NAME}_subtitles.json')
        else:
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

        raw_output_path = output_path.replace('.json', '_raw_analyzed.json')
        try:
            with open(raw_output_path, 'w', encoding='utf-8') as f:
                # 保存的是排序后的、成功处理的、移除了 frame_number 的结果
                json.dump(results_for_processor, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已分析帧的原始结果已保存到 {raw_output_path}")
        except Exception as e:
             self.logger.error(f"保存原始分析结果失败: {e}")

        # --- 6. 使用字幕处理器处理筛选后的结果 ---
        processed_subtitles = []
        if results_for_processor: # 仅当有成功分析结果时才进行处理
            self.logger.info("开始使用 SubtitleProcessor 处理字幕...")
            start_time_processor = time.time()
            try:
                # 动态设置字幕处理器的转录路径
                subtitle_processor = SubtitleProcessor(transcript_path)
                processed_subtitles = subtitle_processor.process_subtitles(results_for_processor, output_path, similarity_threshold)
                processor_duration = time.time() - start_time_processor
                self.logger.info(f"SubtitleProcessor 处理完成，耗时 {processor_duration:.2f} 秒")
            except ValueError as e:
                self.logger.error(f"字幕处理失败: {e}. 请确保视频帧率已正确获取并存储在config中.")
            except Exception as e:
                self.logger.error(f"字幕处理时发生未知错误: {e}")
        else:
            self.logger.warning("没有成功分析的帧结果，无法进行字幕后处理。")
            # 确保即使没有结果，也创建空的输出文件
            if output_path:
                 try:
                     with open(output_path, 'w', encoding='utf-8') as f:
                         json.dump({'subtitles': [], 'output_frame_rate': config.OUTPUT_FRAME_RATE}, f, ensure_ascii=False, indent=2)
                     self.logger.info(f"已创建空的字幕JSON文件: {output_path}")
                 except Exception as e:
                     self.logger.error(f"创建空字幕JSON文件失败: {e}")

        # --- 7. 导出为SRT格式 和 拼接文本 ---
        # (这部分逻辑移到SubtitleProcessor内部或保持现状，取决于设计)
        # 这里假设 SubtitleProcessor 内部处理了导出
        if processed_subtitles:
            srt_output_path = output_path.replace('.json', '.srt')
            combined_text_path = output_path.replace('.json', '_combined.txt') # 使用新的路径名
            try:
                subtitle_processor.export_to_srt(processed_subtitles, srt_output_path)
                self.logger.info(f"处理后的字幕已导出为SRT格式: {srt_output_path}")

                # 拼接字幕文本
                complete_text = "\n".join([sub['text'] for sub in processed_subtitles if 'text' in sub])
                with open(combined_text_path, 'w', encoding='utf-8') as f:
                    f.write(complete_text)
                self.logger.info(f"拼接后的字幕文本已保存到: {combined_text_path}")
                # 更新config中的路径，供后续步骤使用 (如果需要的话)
                # config.SUBTITLES_RESULT_PATH = combined_text_path
            except AttributeError:
                 self.logger.warning("SubtitleProcessor实例可能未初始化，无法导出SRT或拼接文本。")
            except Exception as e:
                self.logger.error(f"导出SRT或拼接字幕文本时出错: {e}")
        else: # 没有处理结果，也创建空文件
             srt_output_path = output_path.replace('.json', '.srt')
             combined_text_path = output_path.replace('.json', '_combined.txt')
             try:
                 with open(srt_output_path, 'w', encoding='utf-8') as f: f.write("")
                 with open(combined_text_path, 'w', encoding='utf-8') as f: f.write("")
                 self.logger.info("已创建空的SRT和拼接文本文件。")
             except Exception as e:
                 self.logger.error(f"创建空SRT或拼接文本文件失败: {e}")

        batch_duration = time.time() - start_time_batch
        self.logger.info(f"analyze_batch 总耗时: {batch_duration:.2f} 秒")
        return processed_subtitles