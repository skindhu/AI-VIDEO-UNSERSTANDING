"""
视频处理模块：负责视频帧提取和音频处理
"""

import os
import subprocess
import shutil
from pathlib import Path
import logging

from . import config  # 导入配置模块


class VideoProcessor:
    """视频处理器，用于提取视频帧和音频"""

    def __init__(self, video_path):
        """
        初始化视频处理器

        Args:
            video_path (str): 视频文件路径
        """
        # 输入校验：检查视频文件是否存在
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        self.video_path = video_path
        self.logger = logging.getLogger("VideoProcessor")
        # 不再需要在初始化时获取原始帧率

    def extract_frames(self, output_dir, frame_rate=1):
        """
        从视频中提取帧

        Args:
            output_dir (str): 输出目录
            frame_rate (int): 每秒提取的帧数 (输出帧率)

        Returns:
            list: 提取的帧路径列表
        """
        # 调用 decode_video_to_frames 实现帧提取功能
        return self.decode_video_to_frames(output_dir, frame_rate)

    def decode_video_to_frames(self, output_folder, frame_rate=1):
        """
        将视频解码为帧图像，并将使用的输出帧率存入全局配置。

        Args:
            video_path (str): 视频文件路径
            output_folder (str): 输出文件夹路径
            frame_rate (int): 每秒提取的帧数 (输出帧率)，默认为1

        Returns:
            list: 提取的帧路径列表
        """

        frames_dir = output_folder
        os.makedirs(frames_dir, exist_ok=True)

        # 构建输出路径模式
        output_pattern = os.path.join(frames_dir, "frame_%06d.png")

        # 构建 FFmpeg 命令 (使用传入的frame_rate作为输出帧率)
        command = [
            'ffmpeg',
            '-i', self.video_path,
            '-vf', f'fps={frame_rate}',
            '-hide_banner',
            '-loglevel', 'error',
            output_pattern
        ]

        # 执行 FFmpeg 命令
        try:
            subprocess.run(command, check=True)
            self.logger.info(f"成功从视频中提取帧 (输出速率 {frame_rate} fps)，保存在 {frames_dir}")

            # --- 关键改动：存储实际使用的输出帧率到全局配置 ---
            if frame_rate is not None and frame_rate > 0:
                 config.OUTPUT_FRAME_RATE = float(frame_rate)
                 self.logger.info(f"已将输出帧率 {config.OUTPUT_FRAME_RATE} 存储到全局配置")
            else:
                 self.logger.warning(f"尝试存储无效的输出帧率: {frame_rate}")
                 # 可以考虑是否在此处设置默认值或清空
                 config.OUTPUT_FRAME_RATE = None

        except subprocess.CalledProcessError as e:
            self.logger.error(f"视频帧提取失败: {e}")
            raise RuntimeError(f"视频帧提取失败: {e}")
        except FileNotFoundError:
            self.logger.error("FFmpeg未安装或不在系统路径中")
            raise RuntimeError("FFmpeg未安装或不在系统路径中")

        # 获取提取的帧列表
        frame_files = sorted([
            os.path.join(frames_dir, f)
            for f in os.listdir(frames_dir)
            if f.startswith("frame_") and f.endswith(".png")
        ])

        return frame_files

    def extract_audio(self, output_path):
        """
        从视频中提取音频

        Args:
            output_path (str): 音频输出路径

        Returns:
            str: 音频文件路径
        """
        # 调用提取音频的具体实现
        return self._extract_audio(self.video_path, output_path)

    def _extract_audio(self, video_path, output_audio_path):
        """
        从视频文件中提取音频

        Args:
            video_path (str): 视频文件路径
            output_audio_path (str): 音频输出路径

        Returns:
            str: 音频文件路径
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(output_audio_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 构建 FFmpeg 命令
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',               # 不包含视频
            '-acodec', 'pcm_s16le',  # WAV 常用编码
            '-ar', '16000',      # 采样率 16kHz
            '-ac', '1',          # 单声道
            '-hide_banner',
            '-loglevel', 'error',
            '-y',                # 覆盖已有文件
            output_audio_path
        ]

        # 执行 FFmpeg 命令
        try:
            subprocess.run(command, check=True)
            self.logger.info(f"成功从视频中提取音频，保存为 {output_audio_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"音频提取失败: {e}")
            raise RuntimeError(f"音频提取失败: {e}")
        except FileNotFoundError:
            self.logger.error("FFmpeg未安装或不在系统路径中")
            raise RuntimeError("FFmpeg未安装或不在系统路径中")

        return output_audio_path