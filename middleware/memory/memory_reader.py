# memory_reader.py
from memory.memory_store import MemoryStore
from memory.embedding_utils import embed_text, embed_paper
from typing import List, Dict, Any

class MemoryReader:
    def __init__(self):
        self.store = MemoryStore()

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取完整用户画像（含原始 metadata + 向量）"""
        metadata = self.store.get_user(user_id)
        if not metadata:
            return {"user_id": user_id, "exists": False}
        return {"user_id": user_id, "exists": True, **metadata}

    def find_relevant_papers(self, user_id: str, query: str = "", top_k: int = 5, category: str = None) -> List[Dict]:
        """基于用户兴趣或查询词找相关论文"""
        user_profile = self.get_user_profile(user_id)
        if not user_profile["exists"]:
            # 用户不存在，用 query 嵌入
            query_emb = embed_text(query) if query else [0.0] * 384  # MiniLM 维度
        else:
            # 用用户兴趣向量
            # 注意：ChromaDB 不直接返回 embedding，需从 metadata 存储？或重新计算
            # 这里简化：假设 metadata 中有 'interest_embedding'
            # 更佳做法：单独维护一个 user_embedding 缓存
            query_emb = user_profile.get("interest_embedding", embed_text(query or "default"))

        return self.store.search_similar_papers(query_emb, top_k=top_k, category_filter=category)

    def get_paper_context(self, paper_id: str) -> Dict[str, Any]:
        """获取论文上下文（用于 Content Planner）"""
        paper_meta = self.store.get_paper(paper_id)
        if not paper_meta:
            return {"error": "Paper not found"}
        
        # 可扩展：自动找相似论文
        paper_emb = embed_paper(paper_meta["title"], paper_meta["abstract"])
        similar = self.store.search_similar_papers(paper_emb, top_k=3)
        
        return {
            "paper": paper_meta,
            "similar_papers": similar
        }