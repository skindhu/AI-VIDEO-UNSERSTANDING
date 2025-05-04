"""
AI服务模块：封装Qwen和Gemini API调用
"""

import os
import base64
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
from google import genai  # 使用新的导入方式
from google.genai import types


class AIService:
    """AI服务接口，封装第三方AI模型API调用"""

    def __init__(self, api_keys=None):
        """
        初始化AI服务

        Args:
            api_keys (dict, optional): 包含不同AI服务的API密钥
        """
        # 加载环境变量
        load_dotenv()

        self.api_keys = api_keys or {}
        self.qwen_api = None
        self.gemini_api = None

        # 初始化各API客户端
        # 对于Qwen API，如果没有在api_keys中指定，则尝试从环境变量中读取
        if 'qwen' in self.api_keys:
            self.qwen_api = QwenAPI(self.api_keys['qwen'])
        else:
            # 即使没有提供API密钥，也初始化QwenAPI
            # QwenAPI会自动从环境变量中读取密钥
            self.qwen_api = QwenAPI()

        if 'gemini' in self.api_keys:
            self.gemini_api = GeminiAPI(self.api_keys['gemini'])
        else:
            # 即使没有提供API密钥，也初始化GeminiAPI
            # GeminiAPI会自动从环境变量中读取密钥
            try:
                self.gemini_api = GeminiAPI()
            except ValueError as e:
                # 如果环境变量中没有Gemini API密钥，则不初始化GeminiAPI
                print(f"注意: {e}")

    def describe_image(self, image_path):
        """
        描述图像内容

        Args:
            image_path (str): 图像文件路径

        Returns:
            str: 图像描述文本
        """
        if self.qwen_api:
            # 将图像转为base64
            image_base64 = self.qwen_api.image_to_base64(image_path)
            return self.qwen_api.extract_subtitles(image_base64)
        else:
            raise ValueError("未配置Qwen API密钥，无法提取图像字幕")

    def summarize_text(self, text, use_gemini=True):
        """
        摘要文本内容

        Args:
            text (str): 需要摘要的文本

        Returns:
            str: 摘要文本
        """
        # 构建提示词
        prompt = f"""请对以下游戏视频字幕内容进行摘要总结：

{text}

请提供一个简洁、全面的总结，概括视频的主要内容和关键点。
总结应该保持连贯、逻辑清晰，并提取内容中最重要的信息。

重要说明：
1. 直接提供总结内容，不要加上"以下是总结"、"总结如下"等引导语
2. 不要在回答中评价自己的总结
3. 不要添加任何元描述或说明
"""

        # 调用 generate_text 方法，使用 Gemini 模型
        return self.generate_text(prompt, use_gemini)

    def generate_text(self, prompt, use_gemini=True):
        """
        使用文本生成模型生成内容

        Args:
            prompt (str): 提示词
            use_gemini (bool, optional): 是否使用Gemini模型，默认为True

        Returns:
            str: 生成的文本
        """
        if use_gemini and self.gemini_api:
            return self.gemini_api.generate_text(prompt)
        elif self.qwen_api:
            return self.qwen_api.generate_text(prompt)
        else:
            raise ValueError("未配置可用的文本生成API")


class QwenAPI:
    """通义千问API封装"""

    def __init__(self, api_key=None, model=None):
        """
        初始化通义千问API

        Args:
            api_key (str, optional): API密钥，如果为None则从环境变量中读取
            model (str, optional): 模型名称，如果为None则使用默认模型
        """
        # 加载环境变量
        load_dotenv()

        # 如果没有提供API密钥，则从环境变量中读取
        self.api_key = api_key or os.getenv('QWEN_API_KEY')

        if not self.api_key:
            raise ValueError("未提供API密钥，也未在环境变量中找到QWEN_API_KEY")

        # 允许在初始化时指定模型
        self.vision_model = "qwen-vl-max-latest"  # 默认视觉模型
        self.text_model = model or "qwen-plus"  # 默认文本模型

        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        # 初始化OpenAI客户端，配置为使用通义千问的API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def extract_subtitles(self, image_base64):
        """
        提取图片中的字幕文本

        Args:
            image_base64 (str): 图片的base64编码

        Returns:
            str: 提取的字幕文本
        """
        try:
            # 构建提示词，明确指示模型提取字幕
            prompt = """请识别并提取这张截图中的字幕文本内容。
字幕是指视频或游戏画面中作为内容解说或对话的文本，通常与画面内容紧密相关。
需要区分字幕与UI界面元素（如菜单、状态栏、计分板、玩家名称等）不同。
只返回真正的字幕文本，忽略所有界面UI元素中的文本。
不要添加任何解释或描述，只输出字幕内容本身。
如果没有识别到任何字幕，请回复'无字幕'。"""

            # 使用OpenAI兼容接口调用通义千问VL模型
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": "You are a helpful assistant."}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ]
            )

            # 提取结果
            if response.choices and len(response.choices) > 0:
                result = response.choices[0].message.content
                return result
            else:
                raise RuntimeError("API返回结果格式异常")

        except Exception as e:
            raise RuntimeError(f"提取字幕失败: {str(e)}")

    def generate_text(self, prompt):
        """
        使用通义千问模型生成文本

        Args:
            prompt (str): 提示词

        Returns:
            str: 生成的文本
        """
        try:
            print(f"使用通义千问模型生成文本: {prompt}")
            # 使用OpenAI兼容接口调用通义千问文本模型
            response = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
            )

            # 提取结果
            if response.choices and len(response.choices) > 0:
                result = response.choices[0].message.content
                return result
            else:
                raise RuntimeError("API返回结果格式异常")

        except Exception as e:
            raise RuntimeError(f"文本生成失败: {str(e)}")

    def image_to_base64(self, image_path):
        """
        将图片转换为base64编码

        Args:
            image_path (str): 图片路径

        Returns:
            str: base64编码的图片
        """
        # 检查文件是否存在
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        try:
            # 读取图片并转换为base64
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"图片转换失败: {str(e)}")


class GeminiAPI:
    """Google Gemini API封装，使用Google Gen AI SDK"""

    def __init__(self, api_key=None):
        """
        初始化Google Gemini API

        Args:
            api_key (str, optional): API密钥，如果为None则从环境变量中读取
        """
        # 加载环境变量
        load_dotenv()

        # 从环境变量或参数获取API密钥
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("未提供Gemini API密钥，也未在环境变量中找到GEMINI_API_KEY")

        # 默认模型和配置
        self.model_name = "gemini-2.5-pro-exp-03-25"
        self.temperature = 0.7  # 默认温度参数

        # 设置API选项并初始化客户端
        self._configure_gemini_api()


    def _configure_gemini_api(self):
        """配置Google Gemini API客户端"""
        # 创建客户端实例
        proxy_url = os.getenv('GEMINI_BASE_URL')
        self.client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(api_version='v1beta', base_url=proxy_url))

        print(f"已初始化Gemini API客户端，使用模型: {self.model_name}")

    def generate_text(self, prompt):
        """
        使用Gemini API生成文本

        Args:
            prompt (str): 提示词

        Returns:
            str: 生成的文本
        """
        try:
            print(f"使用Gemini API生成文本: {prompt}")

            # 使用新的SDK调用方式
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature= self.temperature)
            )

            # 提取并返回生成的文本
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'parts'):
                return ''.join([part.text for part in response.parts if hasattr(part, 'text')])
            else:
                raise RuntimeError("API响应格式异常，无法提取生成的文本")

        except Exception as e:
            raise RuntimeError(f"Gemini API调用失败: {str(e)}")