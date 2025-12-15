# memory_writer.py
from memory_store import MemoryStore
from embedding_utils import embed_user_interest
from typing import List, Dict, Any

class MemoryWriter:
    def __init__(self):
        self.store = MemoryStore()

    def initialize_user(self, user_id: str, initial_style: str = "xiaohongshu"):
        """初始化新用户"""
        # 初始兴趣向量为空
        empty_interest = [0.0] * 384  # MiniLM-L6 维度
        metadata = {
            "style_preference": initial_style,
            "history_summaries": [],
            "topics": [],
            "created_at": "now"
        }
        self.store.add_user(user_id, empty_interest, metadata)

    def update_user_interest(self, user_id: str, new_summary: str, style: str = None):
        """更新用户兴趣（基于新生成的总结）"""
        user_meta = self.store.get_user(user_id)
        if not user_meta:
            self.initialize_user(user_id)
            user_meta = self.store.get_user(user_id)

        # 更新历史
        history = user_meta.get("history_summaries", [])
        history.append(new_summary)
        # 保留最近 10 条
        history = history[-10:]

        # 更新风格
        if style:
            user_meta["style_preference"] = style

        # 重新计算兴趣向量
        interest_vec = embed_user_interest(history)

        # 更新 metadata
        user_meta["history_summaries"] = history
        user_meta["interest_embedding"] = interest_vec  # 存储向量到 metadata（方便 reader 读取）

        self.store.add_user(user_id, interest_vec, user_meta)