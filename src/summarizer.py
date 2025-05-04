"""
内容摘要模块：调用AI服务生成视频内容摘要
"""

import os
import logging
from . import config
from .ai_service import AIService

class Summarizer:
    """内容摘要器，用于生成视频内容的摘要"""

    def __init__(self, ai_service):
        """
        初始化内容摘要器
        """
        self.ai_service = ai_service
        self.logger = logging.getLogger("Summarizer")

    def generate_summary(self, content):
        """
        生成内容摘要并保存到固定路径

        Args:
            content (str): 需要摘要的内容，通常是游戏视频的字幕内容

        Returns:
            str: 生成的摘要
        """
        self.logger.info("开始生成视频内容摘要...")

        try:
            # 调用AI服务生成摘要
            summary = self.ai_service.summarize_text(content, True)

            # 使用配置中的固定输出路径
            output_path = config.SUMMARY_OUTPUT_PATH

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # 保存摘要到文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(summary)

            self.logger.info(f"摘要已成功生成并保存到: {output_path}")
            return summary

        except Exception as e:
            self.logger.error(f"生成摘要失败: {e}")
            raise RuntimeError(f"生成摘要失败: {e}")
