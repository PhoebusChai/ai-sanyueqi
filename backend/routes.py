"""API 路由模块"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from config import OPENAI_API_KEY
import services
from tts_service import tts_service

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


# ========== TTS 语音合成 API ==========

class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """文本转语音"""
    try:
        audio_data = await tts_service.synthesize_async(request.text)
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=speech.wav"}
        )
    except Exception as e:
        print(f"[TTS 错误]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/voice")
async def chat_with_voice(request: ChatRequest):
    """聊天并返回语音 (非流式)"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API Key 未配置")

    try:
        # 获取 AI 回复
        reply = services.chat(request.message)

        # 合成语音
        audio_data = await tts_service.synthesize_async(reply)

        # 返回 JSON + Base64 音频
        import base64
        audio_base64 = base64.b64encode(audio_data).decode()

        return {
            "reply": reply,
            "audio": audio_base64,
            "audio_type": "wav"
        }
    except Exception as e:
        print(f"[错误]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/voice/stream")
async def chat_with_voice_stream(request: ChatRequest):
    """
    流式语音聊天：LLM 流式输出 + 逐句 TTS
    
    返回格式 (SSE):
    - data: {"type": "text", "content": "文本内容"}
    - data: {"type": "audio", "content": "base64音频", "sentence": "对应文本"}
    - data: {"type": "done"}
    """
    import base64
    import json
    import asyncio
    
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API Key 未配置")

    async def generate():
        try:
            buffer = ""
            full_reply = ""
            sentence_end = tts_service._sentence_end
            
            # 获取 LLM 流式输出
            for content in services.chat_stream(request.message):
                if content == "[思考完成]":
                    continue
                
                buffer += content
                full_reply += content
                
                # 发送文本
                yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"
                
                # 检查是否有完整句子
                sentences = tts_service.split_sentences(buffer)
                
                if len(sentences) > 1:
                    # 合成完整的句子
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                            # 在线程池中合成
                            loop = asyncio.get_event_loop()
                            audio = await loop.run_in_executor(
                                None,
                                tts_service._synthesize_single,
                                sentence
                            )
                            if audio:
                                audio_b64 = base64.b64encode(audio).decode()
                                yield f"data: {json.dumps({'type': 'audio', 'content': audio_b64, 'sentence': sentence}, ensure_ascii=False)}\n\n"
                    
                    # 保留最后一个不完整的部分
                    last = sentences[-1]
                    if sentence_end.search(last):
                        # 最后一个也是完整句子
                        loop = asyncio.get_event_loop()
                        audio = await loop.run_in_executor(
                            None,
                            tts_service._synthesize_single,
                            last
                        )
                        if audio:
                            audio_b64 = base64.b64encode(audio).decode()
                            yield f"data: {json.dumps({'type': 'audio', 'content': audio_b64, 'sentence': last}, ensure_ascii=False)}\n\n"
                        buffer = ""
                    else:
                        buffer = last
            
            # 处理剩余文本
            if buffer.strip():
                loop = asyncio.get_event_loop()
                audio = await loop.run_in_executor(
                    None,
                    tts_service._synthesize_single,
                    buffer
                )
                if audio:
                    audio_b64 = base64.b64encode(audio).decode()
                    yield f"data: {json.dumps({'type': 'audio', 'content': audio_b64, 'sentence': buffer}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'full_reply': full_reply}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            print(f"\n[错误]: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
