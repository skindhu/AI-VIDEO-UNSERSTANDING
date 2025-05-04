"""
AI服务模块的测试用例
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import base64

# 导入要测试的模块
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ai_service import AIService, QwenAPI


class TestQwenAPI(unittest.TestCase):
    """测试QwenAPI类"""

    def setUp(self):
        """测试前的设置"""
        # 使用测试API KEY，实际测试时会被mock
        self.api_key = "test_api_key"

        # 设置测试图片路径
        self.test_image_path = 'output/frames/game_video/frame_000013.png'

        # 创建QwenAPI实例
        with patch.dict(os.environ, {'QWEN_API_KEY': self.api_key}):
            self.qwen_api = QwenAPI()

    def test_file_not_found(self):
        """测试文件不存在的情况"""
        with self.assertRaises(FileNotFoundError):
            self.qwen_api.image_to_base64("non_existent_image.jpg")

    def test_extract_subtitles(self):
        """测试提取字幕功能（使用真实数据）"""
        # 跳过测试，如果测试图片不存在
        if not os.path.exists(self.test_image_path):
            self.skipTest(f"测试图片不存在: {self.test_image_path}")
            return

        # 使用环境变量的API密钥，创建真实的QwenAPI实例
        api_key = os.getenv('QWEN_API_KEY')
        if not api_key:
            self.skipTest("缺少QWEN_API_KEY环境变量，无法进行真实API测试")
            return

        qwen_api = QwenAPI(api_key)

        try:
            # 将图片转为base64
            image_base64 = qwen_api.image_to_base64(self.test_image_path)

            # 调用实际API提取字幕
            result = qwen_api.extract_subtitles(image_base64)

            # 验证结果不为空
            self.assertIsNotNone(result)
            self.assertTrue(len(result) > 0)
            print(f"成功从实际图片中提取字幕: {result}")
        except Exception as e:
            self.fail(f"字幕提取失败: {e}")

    @patch('os.getenv')
    def test_init_from_env(self, mock_getenv):
        """测试从环境变量初始化"""
        # 模拟环境变量
        mock_getenv.return_value = "env_api_key"

        # 创建QwenAPI实例
        api = QwenAPI()

        # 验证API密钥从环境变量读取
        self.assertEqual(api.api_key, "env_api_key")
        mock_getenv.assert_called_once_with('QWEN_API_KEY')


class TestAIService(unittest.TestCase):
    """测试AIService类"""

    @patch('os.getenv', return_value='env_qwen_key')
    def setUp(self, mock_getenv):
        """测试前的设置"""
        # 设置没有API密钥的情况，应该从环境变量读取
        self.ai_service_from_env = AIService()

        # 也测试显式提供API密钥的情况
        self.api_keys = {
            'qwen': 'test_qwen_key',
            'gemini': 'test_gemini_key'
        }
        self.ai_service = AIService(self.api_keys)

    @patch('src.ai_service.QwenAPI.image_to_base64')
    @patch('src.ai_service.QwenAPI.extract_subtitles')
    def test_describe_image(self, mock_extract, mock_to_base64):
        """测试describe_image方法"""
        # 设置模拟返回值
        mock_to_base64.return_value = "mock_base64_string"
        mock_extract.return_value = "测试字幕内容"

        # 调用方法
        result = self.ai_service.describe_image("test_image.jpg")

        # 验证结果
        self.assertEqual(result, "测试字幕内容")
        mock_to_base64.assert_called_with("test_image.jpg")
        mock_extract.assert_called_with("mock_base64_string")

    @patch('src.ai_service.QwenAPI.image_to_base64')
    @patch('src.ai_service.QwenAPI.extract_subtitles')
    def test_describe_image_from_env(self, mock_extract, mock_to_base64):
        """测试使用环境变量初始化的服务describe_image方法"""
        # 设置模拟返回值
        mock_to_base64.return_value = "mock_base64_string"
        mock_extract.return_value = "测试字幕内容"

        # 调用方法
        result = self.ai_service_from_env.describe_image("test_image.jpg")

        # 验证结果
        self.assertEqual(result, "测试字幕内容")
        mock_to_base64.assert_called_with("test_image.jpg")
        mock_extract.assert_called_with("mock_base64_string")


if __name__ == '__main__':
    unittest.main()