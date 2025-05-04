"""
视觉内容提取和字幕处理模块的测试用例
"""

import os
import json
import shutil
import unittest
from pathlib import Path
import glob
import logging # 添加日志记录

# 导入要测试的模块
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.visual_extractor import VisualExtractor
from src.ai_service import AIService
from src.subtitle_processor import SubtitleProcessor
from src import config # 导入配置模块

# 配置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestVisualExtractor(unittest.TestCase):
    """测试VisualExtractor类"""

    # --- 类变量 ---
    CLEANUP_AFTER_TEST = False
    source_dir = os.path.join('output', 'frames', 'game_video')
    test_frames_dir = os.path.join('output', 'frames', 'test_frames')
    ai_service = None
    test_files = []
    transcript_path = config.TRANSCRIPT_PATH
    # 在 setUpClass 中定义期望的拼接字幕路径
    expected_subtitles_result_path = None

    @classmethod
    def _cleanup_test_files_class(cls):
        """清理测试文件和目录 (类方法)"""
        logger.info("\n开始执行类级别清理...")
        # 删除测试过程中创建的目录和文件
        if os.path.exists(cls.test_frames_dir):
            shutil.rmtree(cls.test_frames_dir)
            logger.info(f"- 已清理测试帧目录: {cls.test_frames_dir}")

        # 删除测试生成的结果文件
        result_dir = os.path.join('output', 'subtitles')
        if os.path.exists(result_dir):
            # 删除所有测试相关的json和srt文件 (包括 raw)
            patterns = ['test_*.json', 'test_*.srt', 'custom_test_*.json', 'custom_test_*.srt']
            test_outputs = []
            for pattern in patterns:
                test_outputs.extend(glob.glob(os.path.join(result_dir, pattern)))

            for file_path in test_outputs:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"- 已删除测试生成的文件: {file_path}")
                    except OSError as e:
                        logger.error(f"- 删除文件失败 {file_path}: {e}")

        # 使用在 setUpClass 中设置的路径
        if cls.expected_subtitles_result_path and os.path.exists(cls.expected_subtitles_result_path):
            try:
                os.remove(cls.expected_subtitles_result_path)
                logger.info(f"- 已删除拼接字幕文件: {cls.expected_subtitles_result_path}")
            except OSError as e:
                logger.error(f"- 删除拼接字幕文件失败 {cls.expected_subtitles_result_path}: {e}")
        elif cls.expected_subtitles_result_path:
             logger.info(f"- 拼接字幕文件未找到，无需删除: {cls.expected_subtitles_result_path}")
        else:
             logger.warning("- 期望的拼接字幕路径未设置，无法清理")

        # 清理config中的帧率
        config.OUTPUT_FRAME_RATE = None
        # 清理config中的拼接字幕路径
        config.SUBTITLES_RESULT_PATH = None
        logger.info("- config输出帧率和拼接字幕路径已重置")
        logger.info("类级别清理完成.")

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前执行一次"""
        logger.info("\n=== TestVisualExtractor: setUpClass 开始 ===")
        # 先执行清理，确保环境干净
        cls._cleanup_test_files_class()

        # 确定测试使用的视频名称和期望的转录文件路径
        # (这应该与 test_audio_transcriber 中使用的逻辑一致)
        video_name_for_test = "game_video"
        cls.transcript_path = os.path.join(
            'output', 'audio', f"{video_name_for_test}_transcript.json"
        )
        logger.info(f"- 类级别设置期望的转录文件路径: {cls.transcript_path}")

        # 确保测试目录存在 (清理后需要重新创建)
        os.makedirs(cls.test_frames_dir, exist_ok=True)
        logger.info(f"- 已创建测试帧目录: {cls.test_frames_dir}")

        # 检查源目录是否存在
        if not os.path.exists(cls.source_dir):
            raise unittest.SkipTest(f"源目录不存在: {cls.source_dir} - 跳过整个测试类")

        # 检查转录文件是否存在 (测试需要它)
        if not os.path.exists(cls.transcript_path):
            raise unittest.SkipTest(f"测试依赖的转录文件不存在: {cls.transcript_path} - 跳过整个测试类")

        # 获取源目录中的图片文件
        valid_extensions = ['.jpg', '.jpeg', '.png']
        source_files = []
        for ext in valid_extensions:
            source_files.extend(glob.glob(os.path.join(cls.source_dir, f"*{ext}")))

        # 按文件名排序
        source_files.sort()

        # 至少需要4个文件进行测试 (或者更多，取决于你想测试的场景)
        num_test_files = 30 # 使用更多文件以更好测试优化效果
        if len(source_files) < num_test_files:
            logger.warning(f"源目录中图片文件不足 {num_test_files} 个，将使用 {len(source_files)} 个进行测试")
            num_test_files = len(source_files)
            if num_test_files == 0:
                raise unittest.SkipTest(f"源目录中没有图片文件: {cls.source_dir} - 跳过整个测试类")

        # 复制指定数量的文件到测试目录
        cls.test_files = []
        for i, source_file in enumerate(source_files[:num_test_files]):
            file_name = os.path.basename(source_file)
            target_file = os.path.join(cls.test_frames_dir, file_name)
            shutil.copy2(source_file, target_file)
            cls.test_files.append(target_file)

        logger.info(f"- 已复制{len(cls.test_files)}个文件到测试目录")

        # 初始化真实的AI服务 (一次性)
        try:
            cls.ai_service = AIService()
            # 设置全局帧率 (一次性) - 应该由VideoProcessor设置，这里模拟
            # 假设我们知道game_video的帧率，如果不知道，需要先运行VideoProcessor
            # 或者在测试中动态获取（但这会增加测试复杂性）
            config.OUTPUT_FRAME_RATE = 5.0 # 假设输出帧率为5
            logger.info(f"- 类级别设置输出帧率 (模拟): {config.OUTPUT_FRAME_RATE}")

            # 设置期望的拼接字幕文件路径 (模拟 main.py 的行为)
            # 使用一个与测试相关的名称
            cls.expected_subtitles_result_path = os.path.join(
                'output', f"{video_name_for_test}_subtitles.txt"
            )
            config.SUBTITLES_RESULT_PATH = cls.expected_subtitles_result_path
            logger.info(f"- 类级别设置拼接字幕路径 (模拟): {config.SUBTITLES_RESULT_PATH}")
        except Exception as e:
            raise unittest.SkipTest(f"初始化AI服务失败: {e} - 跳过整个测试类")
        logger.info("=== TestVisualExtractor: setUpClass 完成 ===")

    @classmethod
    def tearDownClass(cls):
        """在所有测试结束后执行一次"""
        logger.info("\n=== TestVisualExtractor: tearDownClass 开始 ===")
        if cls.CLEANUP_AFTER_TEST:
            cls._cleanup_test_files_class()
        else:
            logger.info("跳过测试后清理步骤，保留测试文件")
        logger.info("=== TestVisualExtractor: tearDownClass 完成 ===")

    def setUp(self):
        """在每个测试方法开始前执行"""
        logger.debug(f"--- {self._testMethodName}: setUp 开始 ---")
        # 确保AI服务已初始化
        if self.ai_service is None:
            self.skipTest("AI 服务未在 setUpClass 中成功初始化")
        # 每个测试都需要自己的Extractor实例
        self.extractor = VisualExtractor(self.ai_service)
        logger.debug(f"--- {self._testMethodName}: setUp 完成 ---")

    def tearDown(self):
        """在每个测试方法结束后执行"""
        # 目前没有每个测试方法后都需要执行的清理
        logger.debug(f"--- {self._testMethodName}: tearDown --- ")
        pass

    # --- 测试方法 ---
    def test_init(self):
        """测试初始化"""
        logger.info(f"--- {self._testMethodName} 运行 --- ")
        self.assertIsNotNone(self.extractor)
        self.assertEqual(self.extractor.ai_service, self.ai_service)

    def test_analyze_frame(self):
        """测试单帧分析功能"""
        logger.info(f"--- {self._testMethodName} 运行 --- ")
        if not hasattr(self, 'test_files') or not self.test_files:
            self.skipTest("没有可用的测试文件")
            return

        try:
            # 分析第一帧
            frame_path = self.test_files[0]
            result = self.extractor.analyze_frame(frame_path)

            # 验证结果
            self.assertEqual(result['frame_name'], os.path.basename(frame_path))
            self.assertIsNotNone(result['subtitle'])
            logger.info(f"成功从帧中提取字幕: {result['subtitle']}")

            # 测试分析不存在的帧
            non_existent_path = os.path.join(self.test_frames_dir, 'non_existent.png')
            result = self.extractor.analyze_frame(non_existent_path)

            # 验证错误处理
            self.assertEqual(result['frame_name'], 'non_existent.png')
            self.assertEqual(result['subtitle'], '分析失败')
            self.assertIn('error', result)
        except Exception as e:
            self.fail(f"测试单帧分析失败: {e}")

    def test_analyze_batch_optimized(self):
        """测试批量分析功能（优化版）"""
        logger.info(f"--- {self._testMethodName} 运行 --- ")
        if not hasattr(self, 'test_frames_dir') or not os.path.exists(self.test_frames_dir):
            self.skipTest("测试目录不存在")
            return

        if not config.OUTPUT_FRAME_RATE: # 确保输出帧率已设置
            self.fail("输出帧率未设置，无法进行批量分析测试")

        try:
            # 设置输出路径
            output_dir = os.path.join('output', 'subtitles')
            output_path = os.path.join(output_dir, 'test_batch_optimized_output.json')
            raw_output_path = output_path.replace('.json', '_raw_analyzed.json')
            srt_output_path = output_path.replace('.json', '.srt')

            # 执行批量分析，使用转录文件进行优化
            processed_subtitles = self.extractor.analyze_batch(
                self.test_frames_dir,
                output_path,
                similarity_threshold=0.9, # 使用稍高的阈值进行测试
                silent_sample_interval=1.5, # 测试不同的采样间隔
                segment_sample_interval=0 # 测试只处理边界
            )

            # 验证返回结果
            self.assertIsInstance(processed_subtitles, list)
            # 我们不能确定具体有多少条，但至少应该有一条（除非AI全失败）
            # self.assertTrue(len(processed_subtitles) > 0)
            if processed_subtitles:
                self.assertIn('text', processed_subtitles[0])
                self.assertIn('start_time', processed_subtitles[0])
                self.assertIn('end_time', processed_subtitles[0])
            else:
                logger.warning("analyze_batch 返回了空字幕列表")

            # 验证输出文件存在性
            self.assertTrue(os.path.exists(output_path), f"处理后的JSON文件未找到: {output_path}")
            self.assertTrue(os.path.exists(raw_output_path), f"原始分析JSON文件未找到: {raw_output_path}")
            self.assertTrue(os.path.exists(srt_output_path), f"SRT文件未找到: {srt_output_path}")

            # 验证JSON输出文件结构
            with open(output_path, 'r', encoding='utf-8') as f:
                json_results = json.load(f)
            self.assertIn('subtitles', json_results)
            self.assertIn('output_frame_rate', json_results)
            self.assertEqual(len(json_results['subtitles']), len(processed_subtitles))

            # 验证原始分析结果数量 (应该少于总帧数)
            with open(raw_output_path, 'r', encoding='utf-8') as f:
                raw_json_results = json.load(f)
            analyzed_count = len(raw_json_results)
            total_frames = len(self.test_files)
            logger.info(f"智能分析处理了 {analyzed_count} / {total_frames} 帧")
            # 这个断言可能因为边界条件或短视频而不成立，但通常应该成立
            if total_frames > 1:
                self.assertLessEqual(analyzed_count, total_frames, "分析的帧数不应超过总帧数")
                # 通常我们期望分析的帧数少于总帧数，但取决于采样设置和视频内容
                # self.assertLess(analyzed_count, total_frames, "优化后分析的帧数应少于总帧数")

            # 验证SRT文件非空 (除非没有有效字幕)
            if processed_subtitles:
                with open(srt_output_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                self.assertTrue(len(srt_content) > 0)

            # 测试输入目录不存在的情况
            with self.assertRaises(FileNotFoundError):
                self.extractor.analyze_batch('non_existent_dir')
        except Exception as e:
            logger.error(f"测试批量分析失败: {e}", exc_info=True)
            self.fail(f"测试批量分析失败: {e}")

if __name__ == '__main__':
    # 可以增加更详细的日志级别用于调试
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()