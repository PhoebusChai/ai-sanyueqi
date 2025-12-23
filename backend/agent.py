"""Agent 模块 - 多轮工具调用循环"""
import json
from openai import OpenAI

from mcp_tools import MCPToolManager

MAX_TOOL_ROUNDS = 10  # 最大工具调用轮数


class Agent:
    def __init__(self, client: OpenAI, tool_manager: MCPToolManager):
        self.client = client
        self.tool_manager = tool_manager
    
    def run(self, model: str, messages: list, max_tokens: int = 200) -> str:
        """
        Agent 循环：AI 自主决定调用哪些工具、调用顺序，直到生成最终回复
        """
        tools = self.tool_manager.get_openai_tools()
        round_count = 0
        
        while round_count < MAX_TOOL_ROUNDS:
            round_count += 1
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                tools=tools,
            )
            
            message = response.choices[0].message
            
            # 如果没有工具调用，返回最终回复
            if not message.tool_calls:
                return message.content or ""
            
            # 执行工具调用
            print(f"[Agent 第{round_count}轮] 调用 {len(message.tool_calls)} 个工具")
            self._process_tool_calls(messages, message)
        
        # 超过最大轮数，强制生成回复
        print(f"[Agent] 达到最大轮数 {MAX_TOOL_ROUNDS}，强制生成回复")
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    
    def run_until_ready_for_stream(self, model: str, messages: list, max_tokens: int = 200):
        """
        执行工具调用直到准备好流式输出，返回 (messages, tool_called)
        """
        tools = self.tool_manager.get_openai_tools()
        round_count = 0
        tool_called = False
        
        while round_count < MAX_TOOL_ROUNDS:
            round_count += 1
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                tools=tools,
            )
            
            message = response.choices[0].message
            
            if not message.tool_calls:
                break
            
            tool_called = True
            print(f"[Agent 第{round_count}轮] 调用 {len(message.tool_calls)} 个工具")
            self._process_tool_calls(messages, message)
        
        return messages, tool_called
    
    def _process_tool_calls(self, messages: list, message):
        """处理工具调用"""
        # 添加 assistant 消息
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in message.tool_calls
            ]
        })
        
        # 执行每个工具
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments or "{}")
            
            print(f"  [工具]: {tool_name}({json.dumps(arguments, ensure_ascii=False)})")
            result = self.tool_manager.call_tool(tool_name, arguments)
            print(f"  [结果]: {result[:100]}..." if len(result) > 100 else f"  [结果]: {result}")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
