"""API 路由模块"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import OPENAI_API_KEY
import services

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.get("/")
async def root():
    return {"message": "三月七桌宠 API 运行中~"}


@router.post("/chat")
async def chat(request: ChatRequest):
    """普通聊天接口"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API Key 未配置")
    
    try:
        reply = services.chat(request.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        print(f"[错误]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API Key 未配置")
    
    async def generate():
        try:
            for content in services.chat_stream(request.message):
                yield f"data: {content}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"\n[错误]: {str(e)}")
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.delete("/chat/history")
async def clear_history():
    """清空对话历史"""
    services.clear_history()
    return {"message": "对话历史已清空"}


@router.get("/tools")
async def list_tools():
    """列出所有可用工具"""
    return {"tools": services.get_tools()}


@router.post("/tools/reload")
async def reload_tools():
    """重新加载工具配置"""
    tools = services.reload_tools()
    return {"message": "工具配置已重新加载", "tools": tools}
