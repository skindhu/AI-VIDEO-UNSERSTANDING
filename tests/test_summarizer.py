"""
内容摘要模块的测试用例
"""

import os
import unittest
import shutil
import logging

# 导入要测试的模块
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.summarizer import Summarizer
from src.ai_service import AIService # 导入AIService
from src import config

# 配置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSummarizer(unittest.TestCase):
    """测试Summarizer类"""

    # --- 类变量 ---
    CLEANUP_AFTER_TEST = False  # 是否在测试后清理生成的文件
    ai_service = None
    test_summary_output_path = "output/test_summary.txt" # 定义测试专用的输出路径

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前执行一次"""
        logger.info("\n=== TestSummarizer: setUpClass 开始 ===")
        try:
            # 初始化真实的AI服务 (一次性)
            cls.ai_service = AIService()
            logger.info("- AI 服务已初始化")
            # 设置测试期间使用的摘要输出路径
            config.SUMMARY_OUTPUT_PATH = cls.test_summary_output_path
            logger.info(f"- 测试摘要输出路径设置为: {config.SUMMARY_OUTPUT_PATH}")
        except Exception as e:
            raise unittest.SkipTest(f"初始化AI服务失败: {e} - 跳过整个测试类")
        logger.info("=== TestSummarizer: setUpClass 完成 ===")

    @classmethod
    def tearDownClass(cls):
        """在所有测试结束后执行一次"""
        logger.info("\n=== TestSummarizer: tearDownClass 开始 ===")
        if cls.CLEANUP_AFTER_TEST:
            # 使用测试期间设置的路径进行清理
            if config.SUMMARY_OUTPUT_PATH and os.path.exists(config.SUMMARY_OUTPUT_PATH):
                try:
                    os.remove(config.SUMMARY_OUTPUT_PATH)
                    logger.info(f"已删除测试生成的摘要文件: {config.SUMMARY_OUTPUT_PATH}")
                except OSError as e:
                    logger.error(f"删除摘要文件失败 {config.SUMMARY_OUTPUT_PATH}: {e}")
            elif config.SUMMARY_OUTPUT_PATH:
                 logger.info(f"摘要文件未找到，无需删除: {config.SUMMARY_OUTPUT_PATH}")
            else:
                 logger.warning("摘要文件路径未设置，无法清理")
        else:
            logger.info("跳过测试后清理步骤")

        # 重置config中的路径
        config.SUMMARY_OUTPUT_PATH = os.path.join('output', 'final_summary.txt') # 恢复默认值
        logger.info(f"- 配置中的摘要路径已重置为默认值: {config.SUMMARY_OUTPUT_PATH}")
        logger.info("=== TestSummarizer: tearDownClass 完成 ===")

    def setUp(self):
        """在每个测试方法开始前执行"""
        logger.debug(f"--- {self._testMethodName}: setUp 开始 ---")
        # 确保AI服务已初始化
        if self.ai_service is None:
            self.skipTest("AI 服务未在 setUpClass 中成功初始化")
        # 每个测试都需要自己的Summarizer实例，并传入AI服务
        self.summarizer = Summarizer(self.ai_service)
        logger.debug(f"--- {self._testMethodName}: setUp 完成 ---")

    def test_generate_summary(self):
        """测试生成摘要功能"""
        logger.info(f"--- {self._testMethodName} 运行 --- ")

        # 准备测试数据
        test_content = """
游戏开始了，我们的角色是一位探险家，正在古老的丛林中寻找失落的遗迹。
这座遗迹据说隐藏着古代文明的秘密。
我们需要通过解决各种谜题和避开陷阱才能到达中心区域。
在途中，我们遇到了一位神秘的指引者，他告诉我们需要收集三件神器才能开启最终的大门。
第一件神器藏在悬崖边的一个洞穴中，守卫是一群凶猛的野兽。
我们成功击败了守卫，获得了第一件神器：太阳之眼。
接下来我们需要前往沼泽地带寻找第二件神器：月亮之泪。
途中遇到了许多困难，包括有毒的植物和危险的流沙。
在沼泽深处，我们找到了被水草包围的月亮之泪。
最后一件神器：星辰之心，位于山顶的古老神庙中。
攀爬山峰的过程异常艰难，我们几乎放弃了。
但最终我们到达了山顶，在与神庙守护者的战斗后获得了星辰之心。
集齐三件神器后，我们回到了遗迹的中心区域。
将三件神器放入相应的凹槽中，大门缓缓打开。
门后是一个巨大的宝库，里面不仅有无数的财宝，还有记载着古代文明知识的卷轴。
我们的探险终于成功了，这将改变世界对这个古代文明的认知。
"""

        try:
            # 预先删除可能存在的旧测试文件
            if os.path.exists(self.test_summary_output_path):
                os.remove(self.test_summary_output_path)

            # 执行摘要生成
            summary = self.summarizer.generate_summary(test_content)

            # 验证结果
            self.assertIsNotNone(summary)
            self.assertTrue(len(summary) > 0)
            logger.info(f"生成的摘要: {summary}")

            # 验证文件生成 (使用测试定义的路径)
            self.assertTrue(os.path.exists(self.test_summary_output_path))
            with open(self.test_summary_output_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            self.assertEqual(summary, file_content)

        except Exception as e:
            logger.error(f"测试生成摘要失败: {e}", exc_info=True)
            self.fail(f"测试生成摘要失败: {e}")

if __name__ == '__main__':
    unittest.main()