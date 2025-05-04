"""
音频转录模块：将音频转换为文本
"""

import os
import json
import whisper
from src import config


class AudioTranscriber:
    """音频转录器，用于将音频转换为文本"""

    def __init__(self, model_size="tiny"):
        """
        初始化音频转录器

        Args:
            model_size (str): Whisper模型大小（https://github.com/openai/whisper），默认为"tiny", 可选"base", "small", "medium", "large", "turbo"
        """
        self.model_size = model_size
        self.model = None

    def load_model(self):
        """
        加载Whisper模型

        Returns:
            object: 加载的Whisper模型
        """
        if self.model is None:
            try:
                self.model = whisper.load_model(self.model_size)
                print(f"Whisper {self.model_size} 模型加载成功")
            except Exception as e:
                raise RuntimeError(f"加载 Whisper 模型 '{self.model_size}' 失败: {e}")
        return self.model

    def transcribe(self, audio_path):
        """
        将音频文件转录为文本

        Args:
            audio_path (str): 音频文件路径
            output_path (str, optional): 输出文件路径，如果提供则保存转录结果到文件

        Returns:
            dict: 转录结果，包含文本和时间戳
        """
        # 使用静态方法进行转录
        result = self.transcribe_audio(audio_path, self.model_size)
        return result

    @staticmethod
    def transcribe_audio(audio_path, model_size="tiny"):
        """
        使用Whisper模型将音频转录为文本

        Args:
            audio_path (str): 音频文件路径
            model_size (str): Whisper模型大小，默认为"tiny"

        Returns:
            dict: 转录结果，包含文本和时间戳等信息
        """

        output_path = config.TRANSCRIPT_PATH
        # 输入校验：检查音频文件是否存在
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        # 如果提供了输出路径，确保输出目录存在
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

        # 加载Whisper模型
        try:
            model = whisper.load_model(model_size)
        except Exception as e:
            raise RuntimeError(f"加载 Whisper 模型 '{model_size}' 失败: {e}")

        # 执行转录
        try:
            result = model.transcribe(audio_path, fp16=False)  # fp16=False 可能在某些CPU上更稳定

            # 如果提供了输出路径，保存转录结果到文件
            if output_path:
                AudioTranscriber.save_transcription(result, output_path)

            return result
        except Exception as e:
            raise RuntimeError(f"Whisper 转录失败: {e}")

    @staticmethod
    def get_text_from_result(result):
        """
        从转录结果中提取纯文本

        Args:
            result (dict): 转录结果

        Returns:
            str: 提取的文本
        """
        return result.get("text", "")

    @staticmethod
    def save_transcription(result, output_path):
        """
        保存转录结果到文件 (JSON和TXT两种格式)。

        Args:
            result (dict): 转录结果。
            output_path (str): 输出文件的基础路径 (扩展名会被忽略或替换)。
                               例如，提供 "output/audio/video_transcript"，
                               将保存为 "video_transcript.json" 和 "video_transcript.txt"。
        """
        if not output_path:
            print("警告: 未提供输出路径，不保存转录结果。")
            return

        try:
            # 确定基础文件名和目录
            output_dir = os.path.dirname(output_path)
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # 定义JSON和TXT文件路径
            json_output_path = os.path.join(output_dir, f"{base_name}.json")
            txt_output_path = os.path.join(output_dir, f"{base_name}.txt")

            # --- 保存JSON文件 ---
            # 提取segments并简化
            segments = result.get("segments", [])
            filtered_segments = []
            for segment in segments:
                filtered_segment = {
                    "id": segment.get("id", 0),
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", "").strip() # 去除首尾空格
                }
                filtered_segments.append(filtered_segment)

            simplified_result = {
                "text": result.get("text", "").strip(),
                "segments": filtered_segments
            }

            with open(json_output_path, 'w', encoding='utf-8') as f_json:
                json.dump(simplified_result, f_json, ensure_ascii=False, indent=2)
            print(f"转录结果 (JSON) 已保存到: {json_output_path}")

            # --- 保存TXT文件 ---
            # 按分段连接，用逗号隔开 (保持之前的逻辑)
            if filtered_segments:
                # 使用处理过的、strip()过的文本
                segmented_text = "，".join([seg['text'] for seg in filtered_segments if seg['text']])
            else:
                # 如果没有分段，使用完整的、strip()过的文本
                segmented_text = simplified_result["text"]

            with open(txt_output_path, 'w', encoding='utf-8') as f_txt:
                f_txt.write(segmented_text)
            print(f"转录结果 (TXT) 已保存到: {txt_output_path}")

        except Exception as e:
            print(f"保存转录结果失败: {e}")
            raise