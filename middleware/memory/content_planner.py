# content_planner.py
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from memory.memory_reader import MemoryReader

# 可选：使用 Jinja2 渲染模板（更灵活）
try:
    from jinja2 import Template
    HAS_JINJA = True
except ImportError:
    HAS_JINJA = False

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
PROMPT_DIR = PROJECT_ROOT / "prompts"

class ContentPlanner:
    def __init__(self):
        self.reader = MemoryReader()
        self.prompt_templates = self._load_prompt_templates()

    def _load_prompt_templates(self) -> Dict[str, str]:
        """加载预定义的 Prompt 模板"""
        styles = ["academic", "simple", "xiaohongshu"]
        templates = {}
        for style in styles:
            path = PROMPT_DIR / f"{style}.txt"
            if path.exists():
                templates[style] = path.read_text(encoding="utf-8")
            else:
                # 内置默认模板（兼容无文件情况）
                templates[style] = self._get_builtin_template(style)
        return templates

    def _get_builtin_template(self, style: str) -> str:
        """内置默认 Prompt 模板"""
        templates = {
            "academic": """
你是一位严谨的科研人员，请基于以下信息撰写一篇学术风格的论文解读：

【当前论文】
标题：{{ title }}
摘要：{{ abstract }}

【用户背景】
- 偏好风格：学术严谨
- 历史关注主题：{{ user_topics_str }}
{% if similar_papers %}
【相关研究】
以下是与当前论文高度相关的先前工作：
{% for paper in similar_papers %}
- {{ paper.title }} (相似度: {{ "%.2f"|format(paper.similarity) }})
  摘要：{{ paper.abstract|truncate(150) }}
{% endfor %}
{% endif %}

请撰写 300-500 字的解读，包含：研究动机、方法创新、实验结果、领域意义。避免主观评价，保持客观。
""",
            "simple": """
请用通俗易懂的语言解释这篇论文，就像给非专业人士讲故事：

【论文】
《{{ title }}》
摘要：{{ abstract }}

【用户可能关心】
- 之前读过关于 {{ user_topics_str }} 的内容
{% if similar_papers %}
- 这篇与以下研究有关联：
{% for paper in similar_papers %}
  • {{ paper.title }}
{% endfor %}
{% endif %}

要求：200-300 字，避免术语，用生活化类比，突出“为什么重要”。
""",
            "xiaohongshu": """
请将这篇 AI 论文总结成小红书爆款笔记！

【论文信息】
标题：{{ title }}
摘要：{{ abstract }}

【用户画像】
- 喜欢轻松活泼但专业的风格
- 关注：{{ user_topics_str }}

{% if similar_papers %}
【领域上下文】
最近相关热门研究：
{% for paper in similar_papers %}
🔥 {{ paper.title }}
{% endfor %}
{% endif %}

要求：
1. 开头抓眼球（用 emoji + 痛点/悬念）
2. 3-4 个要点，每点以 emoji 开头
3. 语言活泼，带点“闺蜜聊天”感
4. 结尾引导互动（如“你怎么看？”）
5. 总字数 150-250 字
"""
        }
        return templates.get(style, templates["xiaohongshu"])

    def build_enhanced_prompt(
        self,
        user_id: str,
        paper_metadata: Dict[str, Any],
        style: str = "xiaohongshu",
        max_similar: int = 3
    ) -> Dict[str, Any]:
        """
        构建增强 Prompt
        
        返回:
        {
            "prompt": "最终拼接好的字符串",
            "context": { ... }  # 用于日志/调试
        }
        """
        # 1. 获取用户画像
        user_profile = self.reader.get_user_profile(user_id)
        user_exists = user_profile.get("exists", False)
        
        if user_exists:
            history_summaries = user_profile.get("history_summaries", [])
            style_pref = user_profile.get("style_preference", style)
            # 提取高频主题（简化：取历史摘要关键词，这里用前3个摘要代表）
            user_topics = list(set(
                [s[:30] for s in history_summaries[-3:] if s]
            )) or ["AI", "机器学习"]
            user_topics_str = "、".join(user_topics[:3])
        else:
            # 新用户
            user_topics_str = "人工智能前沿研究"
            style_pref = style
            history_summaries = []

        # 2. 获取相似论文
        paper_emb = None  # 我们不在此处重新嵌入，假设已存入 ChromaDB
        similar_papers = []
        try:
            # 使用论文 ID 查询上下文（含相似论文）
            context = self.reader.get_paper_context(paper_metadata["paper_id"])
            similar_papers = [
                {
                    "title": p["metadata"]["title"],
                    "abstract": p["metadata"]["abstract"],
                    "similarity": p["similarity"]
                }
                for p in context.get("similar_papers", [])
                if p["similarity"] > 0.3  # 过滤低相似度
            ][:max_similar]
        except Exception as e:
            print(f"⚠️ 获取相似论文失败: {e}")

        # 3. 准备模板变量
        template_vars = {
            "title": paper_metadata["title"],
            "abstract": paper_metadata["abstract"],
            "user_topics_str": user_topics_str,
            "similar_papers": similar_papers,
            "style": style_pref
        }

        # 4. 渲染 Prompt
        template_str = self.prompt_templates.get(style_pref, self.prompt_templates["xiaohongshu"])
        
        if HAS_JINJA:
            template = Template(template_str)
            final_prompt = template.render(**template_vars)
        else:
            # 简易字符串替换（不支持循环/条件）
            final_prompt = template_str
            final_prompt = final_prompt.replace("{{ title }}", paper_metadata["title"])
            final_prompt = final_prompt.replace("{{ abstract }}", paper_metadata["abstract"][:200])
            final_prompt = final_prompt.replace("{{ user_topics_str }}", user_topics_str)

        return {
            "prompt": final_prompt.strip(),
            "context": {
                "user_id": user_id,
                "style": style_pref,
                "user_topics": user_topics_str,
                "similar_papers_count": len(similar_papers),
                "paper_id": paper_metadata["paper_id"]
            }
        }