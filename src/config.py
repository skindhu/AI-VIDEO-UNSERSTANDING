"""
全局配置模块
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- 基本路径配置 ---
OUTPUT_DIR = "output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
SUBTITLES_DIR = os.path.join(OUTPUT_DIR, "subtitles")

# --- 动态配置变量 (将在main.py中设置) ---
VIDEO_NAME = None # 视频文件名 (无扩展名)
OUTPUT_FRAME_RATE = 1 # 默认每秒提取1帧，会被命令行参数覆盖
TRANSCRIPT_PATH = None # 转录JSON文件路径
SUBTITLES_JSON_PATH = None # 字幕JSON文件路径
SUBTITLES_SRT_PATH = None # 字幕SRT文件路径
SUBTITLES_RESULT_PATH = None # 合并字幕文本文件路径
SUMMARY_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "final_summary.txt") # 摘要文件路径

# --- 字幕处理配置 ---
SUBTITLE_MERGE_THRESHOLD_SIMILARITY = 0.95 # 字幕合并相似度阈值
SUBTITLE_MERGE_THRESHOLD_TIME = 1.0       # 字幕合并时间间隔阈值（秒）
MIN_VALID_SUBTITLE_LENGTH = 50 # 字幕内容有效性的最小总长度阈值（字符数）

# --- 视频元数据配置 ---
VIDEO_DESCRIPTION = ''

# --- 多线程配置 ---
VISUAL_EXTRACTION_MAX_WORKERS = 8 # 视觉内容提取的最大线程数
