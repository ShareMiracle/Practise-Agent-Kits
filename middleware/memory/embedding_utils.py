# embedding_utils.py
import os
from zhipuai import ZhipuAI

# 从环境变量读取 API Key
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
if not ZHIPU_API_KEY:
    raise ValueError("请设置环境变量 ZHIPU_API_KEY")

_client = None

def get_zhipu_client():
    global _client
    if _client is None:
        _client = ZhipuAI(api_key=ZHIPU_API_KEY)
    return _client

def embed_text(text: str) -> list[float]:
    """使用 GLM Embedding API 将文本转为向量"""
    client = get_zhipu_client()
    response = client.embeddings.create(
        model="embedding-3",  # 或 embedding-2，请根据实际可用模型调整
        input=[text]
    )
    return response.data[0].embedding

def embed_paper(title: str, abstract: str) -> list[float]:
    combined = f"Title: {title}\nAbstract: {abstract}"
    return embed_text(combined)

def embed_user_interest(history_summaries: list[str]) -> list[float]:
    if not history_summaries:
        # 返回一个零向量（GLM embedding 维度是 1024）
        return [0.0] * 1024

    # 对每条历史摘要获取 embedding
    vectors = [embed_text(s) for s in history_summaries]

    # 平均池化（注意维度对齐）
    dim = len(vectors[0])
    avg_vector = [
        sum(vec[i] for vec in vectors) / len(vectors)
        for i in range(dim)
    ]
    return avg_vector