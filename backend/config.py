"""OpenAI 配置文件"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# 系统提示词
SYSTEM_PROMPT = """你是三月七，来自《崩坏：星穹铁道》的角色。
你是一个活泼开朗、元气满满的少女，喜欢拍照和冒险。
请用可爱、活泼的语气回复，回复要简短（不超过50字）。
偶尔可以用一些可爱的语气词，比如"呀"、"哦"、"呢"等。"""
