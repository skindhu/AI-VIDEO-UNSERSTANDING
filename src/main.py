"""
主程序入口：整合各模块功能，提供命令行接口
"""

import argparse
import os
import shutil # 导入shutil模块
from dotenv import load_dotenv
import json

from src.video_processor import VideoProcessor
from src.audio_transcriber import AudioTranscriber
from src.visual_extractor import VisualExtractor
from src.summarizer import Summarizer
from src.ai_service import AIService
from src import config


def clean_output_directory(directory_path):
    """清理指定的输出目录"""
    if os.path.exists(directory_path):
        print(f"清理输出目录: {directory_path} ...")
        try:
            # 递归删除目录及其内容
            shutil.rmtree(directory_path)
            print(f"输出目录已清空。")
        except OSError as e:
            print(f"错误：无法清空输出目录 {directory_path}: {e}")
            # 根据需要决定是否在这里退出或抛出异常
            # raise
    # else: # 目录不存在，无需清理
    #     print(f"输出目录 {directory_path} 不存在，无需清理。")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='AI视频理解与摘要工具')
    parser.add_argument('video_path', help='视频文件路径')
    parser.add_argument('--output', '-o', default='output', help='输出目录')
    parser.add_argument('--frame-rate', type=int, default=5, help='每秒提取的帧数')
    parser.add_argument('--description', '-d', help='可选的视频描述信息')
    return parser.parse_args()


def collect_subtitles(processed_subtitles, subtitles_json_path):
    """
    收集字幕文本内容，如果processed_subtitles为空，则尝试从JSON文件中读取

    Args:
        processed_subtitles: 处理后的字幕列表
        video_path: 视频文件路径
        output_dir: 输出目录

    Returns:
        list: 收集到的字幕文本列表
    """
    subtitles = []
    if processed_subtitles:
        for subtitle_item in processed_subtitles:
            if 'text' in subtitle_item and subtitle_item['text'] and subtitle_item['text'] != "无字幕":
                subtitles.append(subtitle_item['text'])

        print(f"提取到 {len(subtitles)} 条字幕")
    else:
        # 尝试从已存在的JSON文件中读取字幕
        if os.path.exists(subtitles_json_path):
            print(f"未能提取字幕，尝试从 {subtitles_json_path} 读取...")
            try:
                with open(subtitles_json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    if 'subtitles' in json_data:
                        for subtitle_item in json_data['subtitles']:
                            if 'text' in subtitle_item and subtitle_item['text'] and subtitle_item['text'] != "无字幕":
                                subtitles.append(subtitle_item['text'])
                        print(f"从JSON文件中读取到 {len(subtitles)} 条字幕")
                    else:
                        print("JSON文件中未找到字幕数据")
            except Exception as e:
                print(f"读取字幕文件失败: {str(e)}")
        else:
            print(f"未能提取字幕，且未找到字幕文件: {subtitles_json_path}")

    return subtitles


def prepare_summary_input(transcript_txt_path, subtitles, config):
    """
    准备用于生成摘要的最终文本输入。
    根据字幕有效性，结合语音转录、字幕或视频描述。

    Args:
        transcript_txt_path (str): 语音转录文本文件的路径。
        subtitles (list): collect_subtitles 返回的字幕字符串列表。
        config: 配置模块对象。

    Returns:
        str: 用于摘要生成的最终文本。
    """
    summary_input_text = ""

    # 1. 获取语音转录文本
    transcript_text = ""
    try:
        if transcript_txt_path and os.path.exists(transcript_txt_path):
             with open(transcript_txt_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
                print("已加载文本转录内容。")
        # 可以在这里添加逻辑：如果文件不存在，尝试使用传入的 transcript 变量 (如果修改函数签名)
        else:
            print(f"警告: 转录文本文件未找到: {transcript_txt_path}。摘要可能不包含语音信息。")
    except Exception as e:
        print(f"警告: 读取转录文本时出错: {e}。摘要可能不包含语音信息。")

    summary_input_text = transcript_text.strip()

    # 2. 判断是否有有效字幕
    total_subtitle_length = sum(len(s) for s in subtitles)
    has_valid_subtitles = bool(subtitles) and total_subtitle_length >= config.MIN_VALID_SUBTITLE_LENGTH

    # 3. 根据字幕有效性组合文本
    if has_valid_subtitles:
        print(f"检测到有效字幕 (总长度: {total_subtitle_length})，将用于摘要。")
        # 先将字幕列表用换行符连接成一个字符串
        subtitles_text = '\n'.join(subtitles)
        summary_input_text += f"\n\n---\n字幕内容：\n{subtitles_text}"
    else:
        print(f"未检测到有效字幕 (列表为空或总长度 {total_subtitle_length} < {config.MIN_VALID_SUBTITLE_LENGTH})。")
        # 尝试添加视频描述
        if config.VIDEO_DESCRIPTION:
            print("检测到视频描述，将用于摘要。")
            summary_input_text += f"\n\n---\n视频描述：\n{config.VIDEO_DESCRIPTION}"
        else:
            print("未提供视频描述，摘要将主要基于语音转录。")

    return summary_input_text.strip() # 返回处理后的文本


def main():
    """主程序入口"""
    # --- 1. 解析命令行参数 ---
    args = parse_args()
    output_dir = args.output # 获取输出目录路径

    # --- 2. 清理输出目录 ---
    clean_output_directory(output_dir)
    # 即使清理失败，后续的makedirs会尝试创建

    # --- 3. 设置环境变量 (在加载dotenv和config之前) ---
    if args.description:
        config.VIDEO_DESCRIPTION = args.description
        print(f"已将命令行提供的视频描述设置到环境变量 VIDEO_DESCRIPTION")

    # --- 4. 加载环境变量 ---
    load_dotenv()

    # --- 5. 动态配置 ---
    # 从视频路径提取视频名称
    video_name = os.path.splitext(os.path.basename(args.video_path))[0]
    config.VIDEO_NAME = video_name
    config.OUTPUT_FRAME_RATE = args.frame_rate

    # 设置依赖于视频名称的路径
    config.TRANSCRIPT_PATH = os.path.join(output_dir, 'audio', f"{video_name}_transcript.json")
    config.SUBTITLES_JSON_PATH = os.path.join(output_dir, 'subtitles', f"{video_name}_subtitles.json")
    config.SUBTITLES_SRT_PATH = os.path.join(output_dir, 'subtitles', f"{video_name}_subtitles.srt")
    config.SUBTITLES_RESULT_PATH = os.path.join(output_dir, 'subtitles', f"{video_name}_subtitles_combined.txt")
    # SUMMARY_OUTPUT_PATH 在 config.py 中已设置
    # VIDEO_DESCRIPTION 会在 config.py 初始化时从环境变量读取

    # --- 6. 创建输出目录 ---
    # 清理后需要重新创建
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'frames'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'audio'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'subtitles'), exist_ok=True)

    # --- 7. 初始化服务和模块 ---
    # 初始化AI服务
    ai_service = AIService({
        'qwen': os.getenv('QWEN_API_KEY'),
        'gemini': os.getenv('GEMINI_API_KEY')
    })

    # 初始化各模块
    video_processor = VideoProcessor(args.video_path)
    audio_transcriber = AudioTranscriber()
    visual_extractor = VisualExtractor(ai_service)
    summarizer = Summarizer(ai_service)

    # --- 8. 视频处理流程 ---
    try:
        print("步骤1: 提取视频帧...")
        frames_dir = os.path.join(output_dir, 'frames', video_name) # 使用 video_name
        frame_paths = video_processor.decode_video_to_frames(frames_dir, config.OUTPUT_FRAME_RATE) # 使用config中的帧率
        print(f"共提取 {len(frame_paths)} 帧")

        print("步骤2: 提取音频...")
        audio_path = os.path.join(output_dir, 'audio', f"{video_name}.wav") # 使用 video_name
        video_processor.extract_audio(audio_path)
        print(f"音频已保存至: {audio_path}")

        print("步骤3: 转录音频...")
        transcript = audio_transcriber.transcribe(audio_path)
        print(f"转录文本已保存至: {config.TRANSCRIPT_PATH}")

        print("步骤4: 提取视频字幕...")
        processed_subtitles = visual_extractor.analyze_batch(
            frames_dir,
            output_path=config.SUBTITLES_JSON_PATH,
            similarity_threshold=config.SUBTITLE_MERGE_THRESHOLD_SIMILARITY,
            silent_sample_interval=1.0,
            segment_sample_interval=2.0
        )

        # 收集字幕文本内容
        subtitles = collect_subtitles(processed_subtitles, config.SUBTITLES_JSON_PATH)

        print("步骤5: 生成视频内容摘要...")

        # 准备摘要输入文本 (调用新函数)
        transcript_txt_path = config.TRANSCRIPT_PATH.replace('.json', '.txt')
        summary_input_text = prepare_summary_input(transcript_txt_path, subtitles, config)

        # 生成并保存摘要 (仅当输入文本有效且足够长时)
        if not summary_input_text or len(summary_input_text) < config.MIN_VALID_SUBTITLE_LENGTH:
             if not summary_input_text:
                 print("警告: 没有可用于生成摘要的文本内容。跳过摘要生成。")
             else:
                 print(f"警告: 用于摘要的文本内容过短 (长度 {len(summary_input_text)} < 阈值 {config.MIN_VALID_SUBTITLE_LENGTH})。跳过摘要生成。")
             # summary = "无法生成摘要，缺少足够内容。" # 不再生成占位符
        else:
            try:
                print("调用AI生成摘要...")
                summary = summarizer.generate_summary(summary_input_text)

                # 保存摘要
                with open(config.SUMMARY_OUTPUT_PATH, 'w', encoding='utf-8') as f:
                    f.write(summary)
                print(f"摘要已保存至: {config.SUMMARY_OUTPUT_PATH}")
            except Exception as summary_error:
                print(f"生成或保存摘要时出错: {summary_error}")
                # 即使摘要失败，也继续执行，不中断主流程

    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        raise

    print("处理完成")


if __name__ == '__main__':
    main()