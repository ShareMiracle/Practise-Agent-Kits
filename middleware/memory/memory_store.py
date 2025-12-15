# memory_store.py
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import Dict, Any, List
from config import CACHE_DIR

# 确保缓存目录存在
CHROMA_PATH = CACHE_DIR / "chroma"
CHROMA_PATH.mkdir(parents=True, exist_ok=True)

class MemoryStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        # 创建两个集合：papers 和 users
        self.papers_collection = self.client.get_or_create_collection(
            name="papers",
            metadata={"hnsw:space": "cosine"}  # 余弦相似度
        )
        self.users_collection = self.client.get_or_create_collection(
            name="users",
            metadata={"hnsw:space": "cosine"}
        )

    def add_paper(self, paper_id: str, metadata: Dict[str, Any], embedding: List[float]):
        """添加论文向量"""
        self.papers_collection.add(
            ids=[paper_id],
            embeddings=[embedding],
            metadatas=[metadata]
        )

    def add_user(self, user_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """添加/更新用户兴趣向量"""
        self.users_collection.upsert(
            ids=[user_id],
            embeddings=[embedding],
            metadatas=[metadata]
        )

    def get_paper(self, paper_id: str):
        """获取论文元数据"""
        result = self.papers_collection.get(ids=[paper_id])
        return result["metadatas"][0] if result["metadatas"] else None

    def get_user(self, user_id: str):
        """获取用户元数据"""
        result = self.users_collection.get(ids=[user_id])
        return result["metadatas"][0] if result["metadatas"] else None

    def search_similar_papers(self, query_embedding: List[float], top_k: int = 5, category_filter: str = None):
        """语义搜索相似论文"""
        where = {"category": category_filter} if category_filter else None
        results = self.papers_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        return self._format_results(results)

    def search_similar_users(self, query_embedding: List[float], top_k: int = 3):
        """查找兴趣相似的用户（可选）"""
        results = self.users_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return self._format_results(results)

    def _format_results(self, results):
        """标准化返回格式"""
        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        return [
            {
                "id": ids[i],
                "metadata": metadatas[i],
                "similarity": 1 - distances[i]  # 转为相似度 [0,1]
            }
            for i in range(len(ids))
        ]