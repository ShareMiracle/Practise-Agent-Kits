import json
import re
import os
import requests
from datetime import datetime
from typing import Dict, List, Any
from pdf2image import convert_from_path
import fitz  # PyMuPDF

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
    paper_pattern = r'### (.*?)\s*\[\[arxiv\]\(([^)]+)\)\].*?\[\[pdf\]\(([^)]+)\)\]\s*\n>(.*?)(?=\n###|\n## |\Z)'
    
    paper_matches = re.findall(paper_pattern, content, re.DOTALL)
    
    for match in paper_matches:
        title_section = match[0]
        arxiv_url = match[1]
        pdf_url = match[2]
        paper_content = match[3]
        
        paper_data = parse_paper_content(title_section, arxiv_url, pdf_url, paper_content)
        if paper_data:
            papers.append(paper_data)
    
    return papers

def parse_paper_content(title_section: str, arxiv_url: str, pdf_url: str, content: str) -> Dict[str, Any]:
    """
    解析单个论文的内容
    
    Args:
        title_section: 标题部分
        arxiv_url: arXiv URL
        pdf_url: PDF URL
        content: 论文内容
    
    Returns:
        论文数据字典
    """
    paper_id = arxiv_url.split('/')[-1]
    
    paper = {
        "url": f"https://arxiv.org/abs/{paper_id}",
        "pdf_url": pdf_url,
        "title": "",
        "title_zh": "",
        "authors": "",
        "abstract": "",
        "abstract_zh": "",
        "categories": [],
        "first_submitted_date": "",
        "first_announced_date": "",
        "comments": "No comments",
        "paper_id": paper_id,
        "paper_dir": f"papers/{paper_id}",  # 论文目录
        "local_pdf_path": "",
        "images_dir": "",  # 图像目录
        "image_paths": []
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

def download_pdf(pdf_url: str, paper_dir: str, paper_id: str) -> str:
    """
    下载PDF文件到论文目录
    
    Args:
        pdf_url: PDF文件的URL
        paper_dir: 论文目录
        paper_id: 论文ID
    
    Returns:
        本地PDF文件路径
    """
    os.makedirs(paper_dir, exist_ok=True)
    
    local_path = os.path.join(paper_dir, f"{paper_id}.pdf")
    
    # 如果文件已存在，跳过下载
    if os.path.exists(local_path):
        print(f"PDF已存在: {local_path}")
        return local_path
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        print(f"成功下载PDF: {local_path}")
        return local_path
        
    except Exception as e:
        print(f"下载PDF失败 {pdf_url}: {e}")
        return ""

def pdf_to_images(pdf_path: str, images_dir: str, paper_id: str, dpi: int = 150) -> List[str]:
    """
    将PDF转换为图像，保存在论文目录的images文件夹下
    
    Args:
        pdf_path: PDF文件路径
        images_dir: 图像目录路径
        paper_id: 论文ID
        dpi: 图像分辨率
    
    Returns:
        生成的图像路径列表
    """
    if not os.path.exists(pdf_path):
        print(f"PDF文件不存在: {pdf_path}")
        return []
    
    # 创建images目录
    os.makedirs(images_dir, exist_ok=True)
    
    image_paths = []
    
    try:
        # 方法1: 使用pdf2image (推荐)
        images = convert_from_path(pdf_path, dpi=dpi)
        
        for i, image in enumerate(images):
            image_path = os.path.join(images_dir, f"page_{i+1:03d}.jpg")
            image.save(image_path, "JPEG", quality=85)
            image_paths.append(image_path)
            print(f"生成图像: {image_path}")
            
    except Exception as e:
        print(f"使用pdf2image转换失败: {e}")
        try:
            # 方法2: 使用PyMuPDF作为备选
            doc = fitz.open(pdf_path)
            
            for i in range(len(doc)):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                image_path = os.path.join(images_dir, f"page_{i+1:03d}.png")
                pix.save(image_path)
                image_paths.append(image_path)
                print(f"生成图像 (PyMuPDF): {image_path}")
                
            doc.close()
            
        except Exception as e2:
            print(f"使用PyMuPDF转换也失败: {e2}")
    
    return image_paths

def process_all_papers(json_file_path: str, max_papers: int = None) -> Dict[str, Any]:
    """
    处理所有论文：下载PDF并转换为图像
    
    Args:
        json_file_path: JSON文件路径
        max_papers: 最大处理论文数量（用于测试）
    
    Returns:
        更新后的数据
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    processed_count = 0
    total_papers = len(data["papers"])
    
    if max_papers:
        total_papers = min(total_papers, max_papers)
    
    # 创建主目录
    os.makedirs("papers", exist_ok=True)
    
    for i, paper in enumerate(data["papers"][:total_papers]):
        print(f"\n处理论文 {i+1}/{total_papers}: {paper['title'][:50]}...")
        
        # 设置目录路径
        paper_dir = paper["paper_dir"]
        images_dir = os.path.join(paper_dir, "images")
        paper["images_dir"] = images_dir
        
        # 下载PDF
        pdf_path = download_pdf(paper["pdf_url"], paper_dir, paper["paper_id"])
        paper["local_pdf_path"] = pdf_path
        
        if pdf_path:
            # 转换为图像
            image_paths = pdf_to_images(pdf_path, images_dir, paper["paper_id"])
            paper["image_paths"] = image_paths
            processed_count += 1
            
            # 打印图像信息
            print(f"生成 {len(image_paths)} 张图像在: {images_dir}")
        else:
            paper["image_paths"] = []
            print(f"PDF下载失败，跳过图像生成")
    
    # 保存更新后的数据
    updated_json_path = json_file_path.replace('.json', '_with_images.json')
    with open(updated_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n处理完成！成功处理 {processed_count}/{total_papers} 篇论文")
    print(f"更新后的数据已保存到: {updated_json_path}")
    
    return data

def print_directory_structure():
    """打印目录结构"""
    print("\n生成的目录结构:")
    print("papers/")
    if os.path.exists("papers"):
        for paper_dir in os.listdir("papers"):
            if os.path.isdir(os.path.join("papers", paper_dir)):
                print(f"  ├── {paper_dir}/")
                paper_path = os.path.join("papers", paper_dir)
                for item in os.listdir(paper_path):
                    item_path = os.path.join(paper_path, item)
                    if os.path.isdir(item_path):
                        print(f"  │   ├── {item}/")
                        # 显示images目录中的文件数量
                        if item == "images":
                            images = os.listdir(item_path)
                            print(f"  │   │   └── {len(images)} 张图像")
                    else:
                        print(f"  │   ├── {item}")

# 使用示例
if __name__ == "__main__":
    # 首先解析MD文件为JSON
    md_file = "/back-up/lzy/Arxiv_MCP/arxiv_crawler/output_llms/2025-10-15.md"  # 你的MD文件路径
    output_file = "/back-up/lzy/Arxiv_MCP/arxiv_crawler/output_llms/2025-10-15.json"  # 输出JSON文件路径
    
    # 解析MD文件
    result = parse_md_to_json(md_file, output_file)
    
    # 打印处理结果摘要
    print(f"\n解析完成！")
    print(f"总共解析了 {len(result['papers'])} 篇论文")
    print(f"领域白名单: {result['metadata']['category_whitelist']}")
    print(f"关键词: {result['metadata']['keywords']}")
    print(f"搜索日期: {result['metadata']['search_from']} 到 {result['metadata']['search_until']}")
    
    # 显示前几篇论文的标题
    print("\n前3篇论文标题:")
    for i, paper in enumerate(result['papers'][:3], 1):
        print(f"{i}. {paper['title']}")
        print(f"   中文: {paper['title_zh']}")
        print(f"   领域: {paper['categories']}")
        print(f"   目录: {paper['paper_dir']}")
    
    # 下载PDF并转换为图像
    print("\n开始下载PDF并转换为图像...")
    process_all_papers(output_file, max_papers=5)  # 限制为5篇用于测试
    
    # 打印目录结构
    print_directory_structure()