# hakimi_middleware.py
# 功能：读取哈基米语料 + 用户需求 -> 调用国内 LLM 生成 Suno 用的提示词（为主），歌词为可选

import os
import json
import random
from typing import List, Dict, Any, Optional

from zai import ZhipuAiClient
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_zai_api_key


CORPUS_PATH = "output/corpus/hakimi_corpus.jsonl"


def load_hakimi_snippets(
    corpus_path: str = CORPUS_PATH,
    max_snippets: int = 12,
) -> List[str]:
    """
    从爬虫生成的 jsonl 语料中随机抽几条“哈基米语气句子”出来，
    仅用来帮 LLM 理解风格，不是让它照抄。
    """
    snippets: List[str] = []
    if not os.path.exists(corpus_path):
        print(f"⚠️ 找不到语料文件：{corpus_path}，先不使用额外知识。")
        return snippets

    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                text = data.get("text")
                if text and isinstance(text, str):
                    snippets.append(text.strip())
            except json.JSONDecodeError:
                continue

    if not snippets:
        print("⚠️ 语料文件为空或解析失败。")
        return []

    random.shuffle(snippets)
    return snippets[:max_snippets]


def build_messages_for_music_prompt(
    user_need: str,
    hakimi_snippets: List[str],
) -> List[Dict[str, str]]:
    """
    构造发给 LLM 的 messages：
    - system：设定角色 = 哈基米音乐提示词工程师
    - user：包含 用户需求 + 若干哈基米语料 + 让模型只输出 JSON 的指令
    """
    knowledge_block = "\n".join(f"- {s}" for s in hakimi_snippets) if hakimi_snippets else "（无额外语料）"

    system_msg = {
        "role": "system",
        "content": (
            "你是一个“哈基米风格音乐提示词工程师”。"
            "你的任务是：根据用户的需求 + 提供的哈基米相关语料，"
            "为音乐生成模型（如 Suno）设计合适的提示词。"
            "重点：你主要输出“音乐风格描述和标签”，而不是完整歌词。"
        ),
    }

    user_msg = {
        "role": "user",
        "content": f"""
用户需求（他想要什么样的哈基米音乐）：
{user_need}

哈基米相关语气/梗示例（仅供你理解语气和氛围，生成提示词时不必逐字复制）：
{knowledge_block}

请你综合用户需求 + 上面的语气示例，设计一组给 Suno 这类音乐 AI 使用的提示信息。
只允许输出一个 JSON，对象格式如下（不要包含注释）：

{{
  "music_prompt_en": "string, 用英文写一段供 Suno 使用的音乐描述，要求生成的歌曲为日语，不超过 120 个英文单词，包含风格、情绪、节奏、乐器、演唱者大致感觉等，比如 high-pitched cute anime idol female vocal, meme-like, high energy, electronic J-pop 等。",
  "music_prompt_zh": "string，对以上英文提示的中文解释，方便人类阅读。",
  "style_tags": ["tag1", "tag2", "tag3"],
  "use_lyrics": false,
  "lyrics_zh": ""
}}

要求：
1. 默认情况下，不要写完整歌词，只做“音乐提示词工程师”，所以 use_lyrics 默认应为 false。
2. 只有在你认为“加一小段 2-4 行中文 Hook 能明显帮助音乐生成效果”时，可以把 use_lyrics 设为 true，并在 lyrics_zh 里给出那几行短句。
3. music_prompt_en 必须是纯英文，适合作为 Suno 的提示词；可以适当提到“meme-like, abstract, repetitive hook, cute and chaotic”等。
4. 必须是合法 JSON，最外层是一个对象，不要在 JSON 外加任何多余文字，不要加解释。
""",
    }

    return [system_msg, user_msg]

def extract_json_from_text(text: str) -> str:
    """
    从模型输出的文本里，尽量把真正的 JSON 对象部分提取出来：
    - 去掉 ```json / ``` 代码块包裹
    - 截取第一个 { 到 最后一个 } 的内容
    """
    text = text.strip()

    # 如果是 ``` 开头，先把代码块外壳去掉
    if text.startswith("```"):
        lines = text.splitlines()
        # 去掉第一行 ``` / ```json
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        # 去掉最后一行 ```（如果有）
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 再保险一点：只截取第一个 { 到 最后一个 } 之间的内容
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return text.strip()

def generate_music_prompt(
    user_need: str,
    corpus_path: str = CORPUS_PATH,
    model_name: str = "glm-4",
    temperature: float = 0.7,
) -> Optional[Dict[str, Any]]:
    """
    对外暴露的主函数：
    输入：user_need（用户的需求一句话或几句话）
    输出：一个 dict，包含 music_prompt_en / music_prompt_zh / style_tags 等字段
    """
    api_key = get_zai_api_key()
    if not api_key:
        print("❌ ZAI_API_KEY 未配置，请在 .env 文件中设置。")
        print("   提示：运行 'python config.py' 可以创建配置文件模板。")
        return None

    client = ZhipuAiClient(api_key=api_key)

    # 1. 加载哈基米语料
    snippets = load_hakimi_snippets(corpus_path)
    print(f"ℹ️ 本次使用 {len(snippets)} 条哈基米语料作为风格参考。")

    # 2. 构造 messages
    messages = build_messages_for_music_prompt(user_need, snippets)

    # 3. 调用 LLM
    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=800,
    )

    content = resp.choices[0].message.content
    print("---- LLM 原始输出（content）----")
    print(content)
    print("------------ 结束 ------------\n")
    cleaned = extract_json_from_text(content)
    # 4. 解析 JSON
    try:
        data = json.loads(cleaned)
        return data
    except json.JSONDecodeError as e:
        print(f"❌ 无法解析为 JSON：{e}")
        return None


if __name__ == "__main__":
    # 简单命令行测试
    print("=== 哈基米音乐提示词中间件测试 ===")
    user_need = input("请输入你想做的哈基米音乐需求（例如：想要一首很癫又可爱的哈基米电音）：\n> ").strip()
    if not user_need:
        print("❌ 用户需求为空，退出。")
        raise SystemExit

    result = generate_music_prompt(user_need)
    if result is None:
        print("❌ 生成失败。")
    else:
        print("✅ 解析后的结果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        print("\n👉 你接下来可以把下面这段直接丢给 Suno：\n")
        print("=== Suno 英文提示词 music_prompt_en ===")
        print(result.get("music_prompt_en", ""))
        print("\n=== 如果需要歌词，歌词（中文） lyrics_zh ===")
        print(result.get("lyrics_zh", "（use_lyrics 为 false，没有歌词）"))