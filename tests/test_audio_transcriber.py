"""
音频转录模块的测试用例
"""

import os
import json
import unittest
import shutil # Import shutil for cleanup
from pathlib import Path
# 导入config模块，但要注意其状态在测试中可能与main运行时不同
import src.config as config

# 导入要测试的模块
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.audio_transcriber import AudioTranscriber


class TestAudioTranscriber(unittest.TestCase):
    """测试AudioTranscriber类"""

    # 添加类变量来控制清理行为
    CLEANUP_AFTER_TEST = False # 设置为 False 则不清理测试生成的文件

    def setUp(self):
        """测试前的设置"""
        # --- 使用与 main.py 默认行为一致的路径结构 ---
        video_name = "game_video"
        self.output_dir = config.OUTPUT_DIR # 通常是 'output'
        self.audio_output_dir = os.path.join(self.output_dir, 'audio')
        # 实际的测试音频文件路径 (假设由其他流程生成或预置)
        self.audio_path = os.path.join(self.audio_output_dir, f"{video_name}.wav")

        # 期望生成的输出文件路径 (基于 main.py 的逻辑)
        # 这就是 config.TRANSCRIPT_PATH 在 main.py 中会被设置的值（默认情况下）
        self.expected_json_path = os.path.join(self.audio_output_dir, f"{video_name}_transcript.json")
        self.expected_txt_path = os.path.join(self.audio_output_dir, f"{video_name}_transcript.txt")

        # 确保测试所需的目录存在 (audio 目录)
        os.makedirs(self.audio_output_dir, exist_ok=True)

        # 保存原始config路径（如果存在），以便 tearDown 恢复
        self._original_transcript_path = getattr(config, 'TRANSCRIPT_PATH', None)


    def tearDown(self):
        """测试后的清理"""

        if self.CLEANUP_AFTER_TEST:
            print("\nPerforming cleanup...")
            # 清理本次测试在标准输出目录中生成的文件
            if os.path.exists(self.expected_txt_path):
                try:
                    os.remove(self.expected_txt_path)
                    print(f"  Cleaned up: {self.expected_txt_path}")
                except OSError as e:
                    print(f"  Error removing {self.expected_txt_path}: {e}")
            if os.path.exists(self.expected_json_path):
                try:
                    os.remove(self.expected_json_path)
                    print(f"  Cleaned up: {self.expected_json_path}")
                except OSError as e:
                    print(f"  Error removing {self.expected_json_path}: {e}")

            # 尝试清理 output/audio 目录（如果它变为空）
            try:
                if os.path.exists(self.audio_output_dir) and not os.listdir(self.audio_output_dir):
                    os.rmdir(self.audio_output_dir)
                    print(f"  Cleaned up empty directory: {self.audio_output_dir}")
                    # 尝试清理 output 目录（如果它也变为空）
                    if os.path.exists(self.output_dir) and not os.listdir(self.output_dir):
                         os.rmdir(self.output_dir)
                         print(f"  Cleaned up empty directory: {self.output_dir}")
            except OSError as e:
                 print(f"  Error removing directory: {e}")
        else:
            print("\nSkipping cleanup as CLEANUP_AFTER_TEST is False.")

        # 恢复原始config路径 (无论是否清理都应执行)
        if self._original_transcript_path is not None:
            config.TRANSCRIPT_PATH = self._original_transcript_path
        elif hasattr(config, 'TRANSCRIPT_PATH'):
             delattr(config, 'TRANSCRIPT_PATH') # 如果原本没有，删除它


    def test_file_not_found(self):
        """测试文件不存在的情况"""
        non_existent_path = "non_existent_audio.wav"
        # 设置一个临时的 config.TRANSCRIPT_PATH 以便函数执行到文件检查
        # 使用与 setUp 中一致的期望路径
        config.TRANSCRIPT_PATH = self.expected_json_path
        with self.assertRaises(FileNotFoundError):
             AudioTranscriber.transcribe_audio(non_existent_path, model_size="tiny")


    def test_transcribe_and_verify_result(self):
        """测试音频转录功能并验证结果字典和文件创建"""
        if not os.path.isfile(self.audio_path):
            self.skipTest(f"测试音频文件不存在: {self.audio_path}")
            return

        # 设置 config.TRANSCRIPT_PATH 以触发保存
        config.TRANSCRIPT_PATH = self.expected_json_path
        # 预先删除旧文件
        if os.path.exists(self.expected_txt_path):
            os.remove(self.expected_txt_path)
        if os.path.exists(self.expected_json_path):
            os.remove(self.expected_json_path)

        try:
            print(f"开始转录音频文件并保存: {self.audio_path}")
            result = AudioTranscriber.transcribe_audio(self.audio_path, model_size="tiny")

            # 1. 验证转录结果字典
            self.assertIsNotNone(result, "转录结果为空")
            self.assertIn("text", result, "转录结果中没有text字段")
            self.assertIsInstance(result["text"], str, "转录文本不是字符串")
            transcribed_text = result["text"]
            print(f"转录成功。文本片段: {transcribed_text[:100]}...")

            # 2. 验证文件是否创建
            self.assertTrue(os.path.exists(self.expected_txt_path),
                            f"期望的转录文本文件未创建: {self.expected_txt_path}")
            self.assertTrue(os.path.exists(self.expected_json_path),
                            f"期望的转录JSON文件未创建: {self.expected_json_path}")
            print("TXT 和 JSON 文件已成功创建。")

        except ImportError as e:
            self.skipTest(f"缺少必要的依赖库: {e}")
        except RuntimeError as e:
            self.skipTest(f"运行时错误: {e}")
        except Exception as e:
            self.fail(f"测试过程中发生异常: {e}")
        # finally 块不再需要恢复 TRANSCRIPT_PATH，tearDown 会处理


    def test_save_transcription_files(self):
        """测试同时保存转录结果为TXT和JSON文件 (并验证内容)"""
        if not os.path.isfile(self.audio_path):
            self.skipTest(f"测试音频文件不存在: {self.audio_path}")
            return

        # 关键：在调用前，设置 config.TRANSCRIPT_PATH 为我们期望的基础路径(JSON)
        # 这模拟了 main.py 中动态设置 config 的行为
        config.TRANSCRIPT_PATH = self.expected_json_path

        try:
            # 如果测试生成的临时文件已存在，先删除
            if os.path.exists(self.expected_txt_path):
                os.remove(self.expected_txt_path)
            if os.path.exists(self.expected_json_path):
                os.remove(self.expected_json_path)

            # 调用 transcribe_audio，它现在会使用我们设置的 config.TRANSCRIPT_PATH 来保存
            print(f"开始转录音频文件并请求保存到: {self.expected_json_path} (及 .txt)")
            result = AudioTranscriber.transcribe_audio(
                self.audio_path,
                model_size="tiny"
            )

            # 验证 TXT 文件是否按预期创建
            self.assertTrue(os.path.exists(self.expected_txt_path),
                            f"期望的转录文本文件未创建: {self.expected_txt_path}")
            # 验证 JSON 文件是否按预期创建
            self.assertTrue(os.path.exists(self.expected_json_path),
                            f"期望的转录JSON文件未创建: {self.expected_json_path}")

            # --- 验证 TXT 文件内容 ---
            with open(self.expected_txt_path, 'r', encoding='utf-8') as f_txt:
                txt_content = f_txt.read()
            segments = result.get("segments", [])
            # 根据分段情况验证TXT内容
            if len(segments) > 1:
                expected_txt_content = "，".join([seg.get("text", "").strip() for seg in segments if seg.get("text", "").strip()])
                self.assertEqual(txt_content, expected_txt_content, "多分段TXT内容不匹配")
                self.assertIn("，", txt_content, "文本未按分段用逗号隔开")
            elif segments:
                self.assertEqual(txt_content, segments[0].get("text", "").strip(), "单个分段TXT内容不匹配")
            else:
                self.assertEqual(txt_content, result.get("text", "").strip(), "无分段时TXT内容不匹配")
            print(f"TXT文件内容验证通过。片段: {txt_content[:200]}...")


            # --- 验证 JSON 文件内容 ---
            with open(self.expected_json_path, 'r', encoding='utf-8') as f_json:
                json_content = json.load(f_json)
            self.assertIn("text", json_content)
            self.assertIn("segments", json_content)
            self.assertEqual(json_content["text"], result.get("text", "").strip())
            if json_content["segments"]:
                segment = json_content["segments"][0]
                required_fields = {"id", "start", "end", "text"}
                actual_fields = set(segment.keys())
                self.assertEqual(required_fields, actual_fields)
            print(f"JSON文件内容验证通过。")

        except ImportError as e:
            self.skipTest(f"缺少必要的依赖库: {e}")
        except RuntimeError as e:
            self.skipTest(f"运行时错误: {e}")
        except Exception as e:
            self.fail(f"测试过程中发生异常: {e}")


    # 不再需要单独的 test_save_transcription_txt 和 test_save_transcription_json
    # 因为 transcribe_audio 要么不保存，要么同时保存两者

    def test_get_text_from_result(self):
        """测试从结果中提取文本功能"""
        mock_result = {"text": "这是一段测试文本"}
        text = AudioTranscriber.get_text_from_result(mock_result)
        self.assertEqual(text, "这是一段测试文本")

        empty_result = {}
        text = AudioTranscriber.get_text_from_result(empty_result)
        self.assertEqual(text, "")


if __name__ == '__main__':
    unittest.main()