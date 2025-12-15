import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from config import CACHE_DIR

# 用户记忆存储目录
USER_MEMORY_DIR = CACHE_DIR / "user_memories"
USER_MEMORY_DIR.mkdir(exist_ok=True)


class UserMemory:
    """用户记忆管理类，负责存储和更新用户信息、历史交互及兴趣偏好"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_path = USER_MEMORY_DIR / f"{user_id}.json"
        self.data = self._load_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """加载用户记忆（首次使用时初始化）"""
        if self.memory_path.exists():
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 初始化记忆结构
        return {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "preferences": {  # 用户偏好
                "summary_style": "xiaohongshu",  # 默认风格
                "感兴趣的领域": [],
                "避免的主题": []
            },
            "interaction_history": []  # 交互历史
        }
    
    def save(self) -> None:
        """保存记忆到本地文件"""
        self.data["updated_at"] = datetime.now().isoformat()
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.data, ensure_ascii=False, indent=2, fp=f)
    
    def add_interaction(self, query: str, paper_id: str, summary: str) -> None:
        """记录用户交互历史"""
        self.data["interaction_history"].append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "paper_id": paper_id,
            "summary": summary[:100]  # 存储摘要的前100字符
        })
        self.save()
    
    def update_preferences(self, preferences: Dict[str, Any]) -> None:
        """更新用户偏好（如总结风格、感兴趣领域）"""
        self.data["preferences"].update(preferences)
        self.save()
    
    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的交互历史"""
        return self.data["interaction_history"][-limit:]
    
    def get_preferences(self) -> Dict[str, Any]:
        """获取用户偏好设置"""
        return self.data["preferences"]