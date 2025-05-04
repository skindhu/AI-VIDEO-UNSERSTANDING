"""
视频处理模块的测试用例
"""

import os
import shutil
import unittest
from pathlib import Path

# 导入要测试的模块
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.video_processor import VideoProcessor


class TestVideoProcessor(unittest.TestCase):
    """测试VideoProcessor类"""

    def setUp(self):
        """测试前的设置"""
        # 使用正确的测试视频路径
        self.video_path = os.path.join('test_video', 'game_video.mp4')
        self.output_folder = os.path.join('output', 'frames')
        self.output_audio_folder = os.path.join('output', 'audio')
        self.frame_rate = 5

        self.video_name = Path(self.video_path).stem
        self.frames_dir = os.path.join(self.output_folder, self.video_name)

        # 确保输出文件夹存在
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.output_audio_folder, exist_ok=True)

        # 创建VideoProcessor实例
        self.video_processor = VideoProcessor(self.video_path)

    def tearDown(self):
        """测试后的清理"""
        # 清理测试生成的文件(可选)
        if os.path.isfile(self.video_path):
            if os.path.exists(self.frames_dir):
                # 这里注释掉清理代码，以便查看测试结果
                # shutil.rmtree(frames_dir)
                pass

    def test_decode_video_to_frames(self):
        """测试decode_video_to_frames方法"""
        # 确保测试视频文件存在
        if not os.path.isfile(self.video_path):
            self.skipTest(f"测试视频文件不存在: {self.video_path}。请确保此文件存在后再运行测试。")
            return

        try:

            # 调用方法
            frames = self.video_processor.decode_video_to_frames(
                self.frames_dir, self.frame_rate
            )


            # 检查输出目录是否存在
            self.assertTrue(os.path.exists(self.frames_dir), "帧输出目录不存在")

            # 检查是否生成了帧图像
            frame_files = [f for f in os.listdir(self.frames_dir)
                         if f.startswith("frame_") and f.endswith(".png")]
            self.assertTrue(len(frame_files) > 0, "没有生成帧图像")

            # 检查返回的帧路径列表
            self.assertEqual(len(frames), len(frame_files),
                           "返回的帧数量与实际生成的不匹配")

            print(f"成功从视频中提取了 {len(frames)} 帧")

        except Exception as e:
            self.fail(f"测试过程中发生异常: {e}")

    def test_extract_audio(self):
        """测试extract_audio方法"""
        # 确保测试视频文件存在
        if not os.path.isfile(self.video_path):
            self.skipTest(f"测试视频文件不存在: {self.video_path}。请确保此文件存在后再运行测试。")
            return

        # 设置音频输出路径
        video_name = Path(self.video_path).stem
        output_audio_path = os.path.join(self.output_audio_folder, f"{video_name}.wav")

        try:
            # 调用方法
            audio_path = self.video_processor._extract_audio(
                self.video_path, output_audio_path
            )

            # 验证
            # 检查音频文件是否存在
            self.assertTrue(os.path.exists(audio_path), "音频文件不存在")

            # 检查音频文件大小是否合理
            file_size = os.path.getsize(audio_path)
            self.assertGreater(file_size, 0, "音频文件大小为0")

            print(f"成功从视频中提取音频，保存为 {audio_path}，文件大小: {file_size/1024/1024:.2f} MB")

        except Exception as e:
            self.fail(f"测试过程中发生异常: {e}")


if __name__ == '__main__':
    unittest.main()