"""记忆系统模块"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# 数据库路径
DB_PATH = Path(__file__).parent / "memory.db"


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 长期记忆表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'fact',
            importance INTEGER DEFAULT 1,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户档案表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nickname TEXT,
            affection INTEGER DEFAULT 50,
            total_chats INTEGER DEFAULT 0,
            first_meet TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_chat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 初始化用户档案
    cursor.execute("""
        INSERT OR IGNORE INTO user_profile (id) VALUES (1)
    """)
    
    conn.commit()
    conn.close()


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self):
        init_db()
    
    # ========== 长期记忆 ==========
    
    def save_memory(self, content: str, memory_type: str = "fact", 
                    importance: int = 1, keywords: list = None) -> int:
        """保存记忆"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memories (content, memory_type, importance, keywords) VALUES (?, ?, ?, ?)",
            (content, memory_type, importance, json.dumps(keywords or []))
        )
        conn.commit()
        memory_id = cursor.lastrowid
        conn.close()
        return memory_id
    
    def search_memories(self, query: str, limit: int = 5) -> list:
        """搜索相关记忆（改进的匹配策略）"""
        conn = get_db()
        cursor = conn.cursor()
        
        # 关键词列表（过滤常见词）
        stop_words = {"我", "你", "的", "是", "吗", "呢", "啊", "呀", "吧", "了", "什么", "怎么", "猜猜", "知道", "记得"}
        keywords = [w for w in query.lower().split() if w not in stop_words and len(w) > 1]
        
        # 提取中文关键词（简单分词）
        import re
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', query)
        for word in chinese_words:
            if len(word) >= 2 and word not in stop_words:
                keywords.append(word)
        
        results = []
        cursor.execute("SELECT * FROM memories ORDER BY importance DESC, last_accessed DESC")
        
        for row in cursor.fetchall():
            content = row["content"]
            content_lower = content.lower()
            stored_keywords = json.loads(row["keywords"] or "[]")
            stored_keywords_lower = [k.lower() for k in stored_keywords]
            
            score = 0
            
            # 关键词匹配
            for kw in keywords:
                if kw in content_lower:
                    score += 2
                if kw in stored_keywords_lower:
                    score += 2
            
            # 语义相关性（简单规则）
            if "喜欢" in query and "喜欢" in content:
                score += 3
            if "歌" in query and ("歌" in content or "音乐" in content):
                score += 3
            if "名字" in query and ("名字" in content or "叫" in content):
                score += 3
            
            if score > 0:
                results.append({
                    "id": row["id"],
                    "content": content,
                    "type": row["memory_type"],
                    "importance": row["importance"],
                    "score": score
                })
        
        results.sort(key=lambda x: (x["score"], x["importance"]), reverse=True)
        
        # 更新访问时间
        if results:
            ids = [r["id"] for r in results[:limit]]
            cursor.execute(
                f"UPDATE memories SET last_accessed = ? WHERE id IN ({','.join('?' * len(ids))})",
                [datetime.now(), *ids]
            )
            conn.commit()
        
        conn.close()
        return results[:limit]
    
    def get_all_memories(self, limit: int = 20) -> list:
        """获取所有记忆"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM memories ORDER BY importance DESC, created_at DESC LIMIT ?",
            (limit,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def delete_memory(self, memory_id: int) -> bool:
        """删除记忆"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    
    # ========== 用户档案 ==========
    
    def get_user_profile(self) -> dict:
        """获取用户档案"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profile WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}
    
    def update_affection(self, delta: int) -> int:
        """更新好感度"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_profile SET affection = MIN(100, MAX(0, affection + ?)) WHERE id = 1",
            (delta,)
        )
        conn.commit()
        cursor.execute("SELECT affection FROM user_profile WHERE id = 1")
        new_affection = cursor.fetchone()[0]
        conn.close()
        return new_affection
    
    def set_nickname(self, nickname: str):
        """设置用户昵称"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE user_profile SET nickname = ? WHERE id = 1", (nickname,))
        conn.commit()
        conn.close()
    
    def record_chat(self):
        """记录一次聊天"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_profile 
            SET total_chats = total_chats + 1, last_chat = ? 
            WHERE id = 1
        """, (datetime.now(),))
        conn.commit()
        conn.close()
    
    # ========== 记忆上下文 ==========
    
    def get_memory_context(self, user_message: str) -> str:
        """获取记忆上下文（用于增强 system prompt）"""
        parts = []
        
        # 用户档案
        profile = self.get_user_profile()
        if profile.get("nickname"):
            parts.append(f"主人的名字是「{profile['nickname']}」")
        if profile.get("affection"):
            level = self._affection_level(profile["affection"])
            parts.append(f"你对主人的好感度：{level}")
        
        # 相关记忆
        memories = self.search_memories(user_message, limit=3)
        
        # 如果没有匹配到，获取最近的重要记忆
        if not memories:
            memories = self.get_recent_memories(limit=3)
        
        if memories:
            memory_texts = [f"- {m['content']}" for m in memories]
            parts.append("你记得的事情：\n" + "\n".join(memory_texts))
        
        return "\n".join(parts) if parts else ""
    
    def get_recent_memories(self, limit: int = 3) -> list:
        """获取最近的记忆"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        results = [{"id": row["id"], "content": row["content"], "type": row["memory_type"]} 
                   for row in cursor.fetchall()]
        conn.close()
        return results
    
    def _affection_level(self, affection: int) -> str:
        """好感度等级描述"""
        if affection >= 90:
            return "超级喜欢！(๑>◡<๑)"
        elif affection >= 70:
            return "很喜欢~"
        elif affection >= 50:
            return "友好"
        elif affection >= 30:
            return "一般"
        else:
            return "有点陌生"


# 全局实例
memory_manager = MemoryManager()


# ========== 记忆提取器 ==========

EXTRACT_PROMPT = """分析以下对话，提取值得记住的用户信息。

对话：
用户：{user_message}
助手：{assistant_reply}

请判断是否有值得记住的信息（如用户喜好、个人信息、重要事件等）。
如果有，返回 JSON 格式：
{{"should_save": true, "content": "记忆内容", "type": "preference/fact/event", "importance": 1-5, "keywords": ["关键词"]}}

如果没有值得记住的，返回：
{{"should_save": false}}

只返回 JSON，不要其他内容。"""


def extract_memory(client, model: str, user_message: str, assistant_reply: str) -> dict | None:
    """使用 LLM 提取记忆"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": EXTRACT_PROMPT.format(
                    user_message=user_message,
                    assistant_reply=assistant_reply
                )
            }],
            max_tokens=200,
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        if result.get("should_save"):
            memory_manager.save_memory(
                content=result["content"],
                memory_type=result.get("type", "fact"),
                importance=result.get("importance", 1),
                keywords=result.get("keywords", [])
            )
            print(f"[记忆] 已保存: {result['content']}")
            return result
    except Exception as e:
        print(f"[记忆提取失败]: {e}")
    
    return None
