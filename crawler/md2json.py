import json
import re
from datetime import datetime
from typing import Dict, List, Any

def parse_md_to_json(md_file_path: str, output_json_path: str) -> Dict[str, Any]:
    """
    使用正则表达式将MD文件解析为JSON格式并保存
    
    Args:
        md_file_path: 输入的MD文件路径
        output_json_path: 输出的JSON文件路径
    
    Returns:
        解析后的字典数据
    """
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 初始化结果字典
    result = {
        "metadata": {
            "repo_url": "https://github.com/huiyeruzhou/arxiv_crawler",
            "search_from": "",
            "search_until": "",
            "category_whitelist": [],
            "keywords": [],
            "total_papers_found": 0,
            "generated_at": ""
        },
        "papers": []
    }
    
    # 使用正则表达式提取所有元数据
    metadata_patterns = {
        "category_whitelist": r'领域白名单：([^\n]+)',
        "keywords": r'关键词：([^\n]+)',
        "total_papers": r'共有(\d+)篇相关领域论文',
        "date": r'论文全览：(\d{4}-\d{2}-\d{2})'
    }
    
    # 提取领域白名单
    category_match = re.search(metadata_patterns["category_whitelist"], content)
    if category_match:
        categories = re.split(r',\s*', category_match.group(1))
        result["metadata"]["category_whitelist"] = [cat.strip() for cat in categories]
    
    # 提取关键词
    keyword_match = re.search(metadata_patterns["keywords"], content)
    if keyword_match:
        keywords = re.split(r',\s*', keyword_match.group(1))
        result["metadata"]["keywords"] = [kw.strip() for kw in keywords]
    
    # 提取论文总数
    total_match = re.search(metadata_patterns["total_papers"], content)
    if total_match:
        result["metadata"]["total_papers_found"] = int(total_match.group(1))
    
    # 提取日期信息
    date_match = re.search(metadata_patterns["date"], content)
    if date_match:
        result["metadata"]["search_until"] = date_match.group(1)
        result["metadata"]["search_from"] = date_match.group(1)
    
    # 设置生成时间
    result["metadata"]["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    # 使用正则表达式提取所有论文
    papers = extract_papers_with_regex(content)
    result["papers"] = papers
    
    # 保存为JSON文件
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"成功处理 {len(papers)} 篇论文，已保存到: {output_json_path}")
    return result

def extract_papers_with_regex(content: str) -> List[Dict[str, Any]]:
    """
    使用正则表达式从内容中提取所有论文信息
    
    Args:
        content: MD文件内容
    
    Returns:
        论文列表
    """
    papers = []
    
    # 匹配每个论文块的正则表达式
    # 这个模式匹配从###标题开始到下一个###标题或文件结尾的所有内容
    paper_pattern = r'### (.*?)\s*\[\[arxiv\]\(([^)]+)\)\].*?\[\[pdf\]\([^)]+\)\]\s*\n>(.*?)(?=\n###|\n## |\Z)'
    
    paper_matches = re.findall(paper_pattern, content, re.DOTALL)
    
    for match in paper_matches:
        title_section = match[0]
        arxiv_url = match[1]
        paper_content = match[2]
        
        paper_data = parse_paper_content(title_section, arxiv_url, paper_content)
        if paper_data:
            papers.append(paper_data)
    
    return papers

def parse_paper_content(title_section: str, arxiv_url: str, content: str) -> Dict[str, Any]:
    """
    解析单个论文的内容
    
    Args:
        title_section: 标题部分
        arxiv_url: arXiv URL
        content: 论文内容
    
    Returns:
        论文数据字典
    """
    paper = {
        "url": f"https://arxiv.org/abs/{arxiv_url.split('/')[-1]}",
        "title": "",
        "title_zh": "",
        "authors": "",
        "abstract": "",
        "abstract_zh": "",
        "categories": [],
        "first_submitted_date": "",
        "first_announced_date": "",
        "comments": "No comments"
    }
    
    # 提取标题（可能包含中英文）
    title_lines = title_section.strip().split('\n')
    if title_lines:
        # 第一行是英文标题
        paper["title"] = title_lines[0].strip()
        # 如果有第二行，可能是中文标题
        if len(title_lines) > 1 and '标题' in title_lines[1]:
            title_zh_match = re.search(r'标题[:：]\s*(.+)', title_lines[1])
            if title_zh_match:
                paper["title_zh"] = title_zh_match.group(1).strip()
    
    # 提取作者
    authors_match = re.search(r'> \*\*Authors\*\*:\s*(.+?)\s*\n', content)
    if authors_match:
        paper["authors"] = authors_match.group(1).strip()
    
    # 提取提交日期
    submitted_match = re.search(r'> \*\*First submission\*\*:\s*(\d{4}-\d{2}-\d{2})', content)
    if submitted_match:
        paper["first_submitted_date"] = submitted_match.group(1)
    
    # 提取公告日期
    announced_match = re.search(r'> \*\*First announcement\*\*:\s*(\d{4}-\d{2}-\d{2})', content)
    if announced_match:
        paper["first_announced_date"] = announced_match.group(1)
    
    # 提取评论
    comments_match = re.search(r'> \*\*comment\*\*:\s*(.+?)\s*\n', content)
    if comments_match:
        paper["comments"] = comments_match.group(1).strip()
    
    # 提取领域
    field_match = re.search(r'- \*\*领域\*\*:\s*(.+?)\s*\n', content)
    if field_match:
        fields = re.split(r',\s*', field_match.group(1))
        paper["categories"] = [field.strip() for field in fields]
    
    # 提取摘要
    abstract_match = re.search(r'- \*\*摘要\*\*:\s*(.+?)(?=\n\n|\n-|\n\*|\Z)', content, re.DOTALL)
    if abstract_match:
        abstract_text = abstract_match.group(1).strip()
        # 判断是否为中文摘要（包含中文字符）
        if any('\u4e00' <= char <= '\u9fff' for char in abstract_text):
            paper["abstract_zh"] = abstract_text
        else:
            paper["abstract"] = abstract_text
    
    # 如果没有提取到中文摘要，尝试从其他地方获取
    if not paper["abstract_zh"]:
        # 尝试从标题中获取中文信息
        if paper["title_zh"]:
            paper["abstract_zh"] = paper["title_zh"]
        # 或者从领域信息中推断
        elif paper["categories"]:
            paper["abstract_zh"] = f"关于{paper['categories'][0]}领域的研究论文"
    
    return paper

def extract_papers_by_category(content: str) -> List[Dict[str, Any]]:
    """
    另一种方法：按类别提取论文
    
    Args:
        content: MD文件内容
    
    Returns:
        论文列表
    """
    papers = []
    
    # 匹配每个类别部分
    category_pattern = r'## (.*?)\s*\n(.*?)(?=\n## |\Z)'
    category_matches = re.findall(category_pattern, content, re.DOTALL)
    
    for category_match in category_matches:
        category_name = category_match[0].strip()
        category_content = category_match[1]
        
        # 跳过非论文类别（如"论文全览"等）
        if not any(keyword in category_name for keyword in ['人工智能', '计算机视觉', '机器学习']):
            continue
        
        # 提取该类别下的所有论文
        paper_pattern = r'### (.*?)\s*\[\[arxiv\]\(([^)]+)\)\].*?\[\[pdf\]\([^)]+\)\]\s*\n>(.*?)(?=\n###|\n\*|\Z)'
        paper_matches = re.findall(paper_pattern, category_content, re.DOTALL)
        
        for match in paper_matches:
            title_section = match[0]
            arxiv_url = match[1]
            paper_content = match[2]
            
            paper_data = parse_paper_content(title_section, arxiv_url, paper_content)
            if paper_data:
                # 如果没有提取到类别，使用当前类别
                if not paper_data["categories"]:
                    # 从类别名称中提取主要领域
                    category_extract = re.search(r'\((.*?)\)', category_name)
                    if category_extract:
                        paper_data["categories"] = [category_extract.group(1)]
                papers.append(paper_data)
    
    return papers

# 使用示例
if __name__ == "__main__":
    # 示例用法
    md_file = "output_llms/2025-10-15.md"  # 你的MD文件路径
    output_file = "output_llms/2025-10-15.json"  # 输出JSON文件路径
    
    result = parse_md_to_json(md_file, output_file)
    
    # 打印处理结果摘要
    print(f"\n处理完成！")
    print(f"总共处理了 {len(result['papers'])} 篇论文")
    print(f"领域白名单: {result['metadata']['category_whitelist']}")
    print(f"关键词: {result['metadata']['keywords']}")
    print(f"搜索日期: {result['metadata']['search_from']} 到 {result['metadata']['search_until']}")
    
    # 显示前几篇论文的标题
    print("\n前3篇论文标题:")
    for i, paper in enumerate(result['papers'][:3], 1):
        print(f"{i}. {paper['title']}")
        print(f"   中文: {paper['title_zh']}")
        print(f"   领域: {paper['categories']}")