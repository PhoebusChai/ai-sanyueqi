"""业务服务模块"""
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, SYSTEM_PROMPT
from mcp_tools import MCPToolManager
from agent import Agent
from memory import memory_manager, extract_memory

# 初始化
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
tool_manager = MCPToolManager()
agent = Agent(client, tool_manager)

# 对话历史
conversation_history = []


def build_system_prompt(user_message: str) -> str:
    """构建带记忆的系统提示词"""
    memory_context = memory_manager.get_memory_context(user_message)
    if memory_context:
        return f"{SYSTEM_PROMPT}\n\n【记忆信息】\n{memory_context}"
    return SYSTEM_PROMPT


def log_chat(role: str, content: str):
    print(f"[{role}]: {content}")


def chat(message: str) -> str:
    """普通聊天"""
    log_chat("用户", message)
    conversation_history.append({"role": "user", "content": message})
    memory_manager.record_chat()
    
    while len(conversation_history) > 20:
        conversation_history.pop(0)
    
    system_prompt = build_system_prompt(message)
    messages = [{"role": "system", "content": system_prompt}, *conversation_history]
    reply = agent.run(OPENAI_MODEL, messages)
    
    conversation_history.append({"role": "assistant", "content": reply})
    log_chat("三月七", reply)
    
    # 异步提取记忆
    extract_memory(client, OPENAI_MODEL, message, reply)
    
    return reply


def chat_stream(message: str):
    """流式聊天，返回生成器"""
    log_chat("用户", message)
    conversation_history.append({"role": "user", "content": message})
    memory_manager.record_chat()
    
    while len(conversation_history) > 20:
        conversation_history.pop(0)
    
    system_prompt = build_system_prompt(message)
    messages = [{"role": "system", "content": system_prompt}, *conversation_history]
    
    # Agent 处理工具调用
    messages, tool_called = agent.run_until_ready_for_stream(OPENAI_MODEL, messages)
    
    if tool_called:
        yield "[思考完成]"
    
    # 流式生成
    stream = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        max_tokens=200,
        stream=True,
    )

    full_reply = ""
    print("[三月七]: ", end="", flush=True)
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_reply += content
            print(content, end="", flush=True)
            yield content
    print()
    
    conversation_history.append({"role": "assistant", "content": full_reply})
    
    # 提取记忆
    extract_memory(client, OPENAI_MODEL, message, full_reply)


def clear_history():
    """清空对话历史"""
    conversation_history.clear()


def get_tools():
    """获取所有工具"""
    return tool_manager.get_openai_tools()


def reload_tools():
    """重新加载工具"""
    tool_manager.reload()
    return tool_manager.get_openai_tools()
