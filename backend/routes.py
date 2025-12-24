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


class MemoryRequest(BaseModel):
    content: str
    memory_type: str = "fact"
    importance: int = 1
    keywords: list = []


class NicknameRequest(BaseModel):
    nickname: str


class AffectionRequest(BaseModel):
    delta: int


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


# ========== 记忆系统 API ==========

@router.get("/memory")
async def list_memories(limit: int = 20):
    """获取所有记忆"""
    from memory import memory_manager
    return {"memories": memory_manager.get_all_memories(limit)}


@router.post("/memory")
async def add_memory(request: MemoryRequest):
    """添加记忆"""
    from memory import memory_manager
    memory_id = memory_manager.save_memory(
        request.content, request.memory_type, 
        request.importance, request.keywords
    )
    return {"id": memory_id, "message": "记忆已保存"}


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: int):
    """删除记忆"""
    from memory import memory_manager
    if memory_manager.delete_memory(memory_id):
        return {"message": "记忆已删除"}
    raise HTTPException(status_code=404, detail="记忆不存在")


@router.get("/memory/search")
async def search_memories(q: str, limit: int = 5):
    """搜索记忆"""
    from memory import memory_manager
    return {"memories": memory_manager.search_memories(q, limit)}


@router.get("/profile")
async def get_profile():
    """获取用户档案"""
    from memory import memory_manager
    return memory_manager.get_user_profile()


@router.put("/profile/nickname")
async def set_nickname(request: NicknameRequest):
    """设置昵称"""
    from memory import memory_manager
    memory_manager.set_nickname(request.nickname)
    return {"message": f"昵称已设置为「{request.nickname}」"}


@router.put("/profile/affection")
async def update_affection(request: AffectionRequest):
    """更新好感度"""
    from memory import memory_manager
    new_affection = memory_manager.update_affection(request.delta)
    return {"affection": new_affection}
