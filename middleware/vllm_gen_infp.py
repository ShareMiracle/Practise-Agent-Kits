import json
import re
import os
import requests
import base64
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pdf2image import convert_from_path
import fitz  # PyMuPDF

# 假设这是您的VLLM调用模块
from llm import multimodel_if_cache

class PaperProcessor:
    def __init__(self):
        """
        初始化论文处理器
        """
        self.images_base_url = "http://your-server.com/images"  # 修改为您的图片服务器地址
    
    async def call_vllm_api(self, messages: List[Dict], img_base: str = "", max_tokens: int = 2000) -> str:
        """
        调用VLLM API
        
        Args:
            messages: 消息列表
            img_base: 图片base64编码
            max_tokens: 最大token数
        
        Returns:
            API响应
        """
        try:
            user_prompt = ""
            system_prompt = ""
            
            # 分离system和user消息
            for message in messages:
                if message["role"] == "system":
                    system_prompt = message["content"]
                elif message["role"] == "user":
                    user_prompt = message["content"]
            
            result = await multimodel_if_cache(
                user_prompt=user_prompt,
                system_prompt=system_prompt, 
                img_base=img_base,
                messages=messages
            )
            
            return result
            
        except Exception as e:
            print(f"调用VLLM API失败: {e}")
            return ""

    def parse_md_to_json(self, md_file_path: str, output_json_path: str) -> Dict[str, Any]:
        """
        使用正则表达式将MD文件解析为JSON格式并保存
        """
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
        
        metadata_patterns = {
            "category_whitelist": r'领域白名单：([^\n]+)',
            "keywords": r'关键词：([^\n]+)',
            "total_papers": r'共有(\d+)篇相关领域论文',
            "date": r'论文全览：(\d{4}-\d{2}-\d{2})'
        }
        
        # 提取元数据
        category_match = re.search(metadata_patterns["category_whitelist"], content)
        if category_match:
            categories = re.split(r',\s*', category_match.group(1))
            result["metadata"]["category_whitelist"] = [cat.strip() for cat in categories]
        
        keyword_match = re.search(metadata_patterns["keywords"], content)
        if keyword_match:
            keywords = re.split(r',\s*', keyword_match.group(1))
            result["metadata"]["keywords"] = [kw.strip() for kw in keywords]
        
        total_match = re.search(metadata_patterns["total_papers"], content)
        if total_match:
            result["metadata"]["total_papers_found"] = int(total_match.group(1))
        
        date_match = re.search(metadata_patterns["date"], content)
        if date_match:
            result["metadata"]["search_until"] = date_match.group(1)
            result["metadata"]["search_from"] = date_match.group(1)
        
        result["metadata"]["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        papers = self.extract_papers_with_regex(content)
        result["papers"] = papers
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"成功处理 {len(papers)} 篇论文，已保存到: {output_json_path}")
        return result

    def extract_papers_with_regex(self, content: str) -> List[Dict[str, Any]]:
        """提取所有论文信息"""
        papers = []
        paper_pattern = r'### (.*?)\s*\[\[arxiv\]\(([^)]+)\)\].*?\[\[pdf\]\(([^)]+)\)\]\s*\n>(.*?)(?=\n###|\n## |\Z)'
        paper_matches = re.findall(paper_pattern, content, re.DOTALL)
        
        for match in paper_matches:
            title_section = match[0]
            arxiv_url = match[1]
            pdf_url = match[2]
            paper_content = match[3]
            
            paper_data = self.parse_paper_content(title_section, arxiv_url, pdf_url, paper_content)
            if paper_data:
                papers.append(paper_data)
        
        return papers

    def parse_paper_content(self, title_section: str, arxiv_url: str, pdf_url: str, content: str) -> Dict[str, Any]:
        """解析单个论文内容"""
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
            "paper_dir": f"papers/{paper_id}",
            "local_pdf_path": "",
            "images_dir": "",
            "image_paths": [],
            "xiaohongshu_content": "",  # 小红书文案
            "selected_images": []  # 选择的图片
        }
        
        # 提取标题
        title_lines = title_section.strip().split('\n')
        if title_lines:
            paper["title"] = title_lines[0].strip()
            if len(title_lines) > 1 and '标题' in title_lines[1]:
                title_zh_match = re.search(r'标题[:：]\s*(.+)', title_lines[1])
                if title_zh_match:
                    paper["title_zh"] = title_zh_match.group(1).strip()
        
        # 提取其他信息...
        authors_match = re.search(r'> \*\*Authors\*\*:\s*(.+?)\s*\n', content)
        if authors_match:
            paper["authors"] = authors_match.group(1).strip()
        
        submitted_match = re.search(r'> \*\*First submission\*\*:\s*(\d{4}-\d{2}-\d{2})', content)
        if submitted_match:
            paper["first_submitted_date"] = submitted_match.group(1)
        
        announced_match = re.search(r'> \*\*First announcement\*\*:\s*(\d{4}-\d{2}-\d{2})', content)
        if announced_match:
            paper["first_announced_date"] = announced_match.group(1)
        
        field_match = re.search(r'- \*\*领域\*\*:\s*(.+?)\s*\n', content)
        if field_match:
            fields = re.split(r',\s*', field_match.group(1))
            paper["categories"] = [field.strip() for field in fields]
        
        abstract_match = re.search(r'- \*\*摘要\*\*:\s*(.+?)(?=\n\n|\n-|\n\*|\Z)', content, re.DOTALL)
        if abstract_match:
            abstract_text = abstract_match.group(1).strip()
            if any('\u4e00' <= char <= '\u9fff' for char in abstract_text):
                paper["abstract_zh"] = abstract_text
            else:
                paper["abstract"] = abstract_text
        
        return paper

    def download_pdf(self, pdf_url: str, paper_dir: str, paper_id: str) -> str:
        """下载PDF文件"""
        os.makedirs(paper_dir, exist_ok=True)
        local_path = os.path.join(paper_dir, f"{paper_id}.pdf")
        
        if os.path.exists(local_path):
            print(f"PDF已存在: {local_path}")
            return local_path
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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

    def pdf_to_images(self, pdf_path: str, images_dir: str, paper_id: str, dpi: int = 150) -> List[str]:
        """PDF转图像"""
        if not os.path.exists(pdf_path):
            print(f"PDF文件不存在: {pdf_path}")
            return []
        
        os.makedirs(images_dir, exist_ok=True)
        image_paths = []
        
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            for i, image in enumerate(images):
                image_path = os.path.join(images_dir, f"page_{i+1:03d}.jpg")
                image.save(image_path, "JPEG", quality=85)
                image_paths.append(image_path)
                print(f"生成图像: {image_path}")
                
        except Exception as e:
            print(f"使用pdf2image转换失败: {e}")
            try:
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

    async def generate_xiaohongshu_content(self, paper: Dict[str, Any]) -> str:
        """
        生成小红书文案
        
        Args:
            paper: 论文数据
        
        Returns:
            小红书文案
        """
        prompt = f"""
请根据以下论文信息生成一篇适合小红书平台的内容文案：

论文标题：{paper['title']}
中文摘要：{paper.get('abstract_zh', '暂无中文摘要')}
研究领域：{', '.join(paper['categories'])}
提交日期：{paper['first_submitted_date']}
发布日期：{paper['first_announced_date']}
论文链接：{paper['url']}

要求：
1. 文案要生动有趣，适合小红书用户阅读
2. 包含论文的核心创新点和价值
3. 突出论文的实用性和应用场景
4. 使用适当的emoji和分段
5. 包含相关的研究领域标签
6. 控制在500字以内

请生成完整的小红书文案：
"""
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的科技内容创作者，擅长将学术论文转化为通俗易懂的社交媒体内容。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        print(f"正在为论文《{paper['title']}》生成小红书文案...")
        content = await self.call_vllm_api(messages)
        
        if not content:
            # 如果API调用失败，生成默认文案
            content = self.generate_default_content(paper)
        
        return content

    def generate_default_content(self, paper: Dict[str, Any]) -> str:
        """生成默认的小红书文案"""
        categories_str = "、".join(paper['categories'])
        
        content = f"""
📚 最新论文推荐：《{paper['title']}》

🎯 研究领域：{categories_str}
📅 发布时间：{paper['first_announced_date']}

🌟 核心亮点：
{paper.get('abstract_zh', '这项研究在相关领域提出了创新性的方法和见解')}

💡 实用价值：
这项研究为相关领域的发展提供了重要参考，具有很好的应用前景。

🔗 论文链接：{paper['url']}

#{categories_str.replace('、', ' #')} #学术研究 #论文分享
"""
        return content.strip()

    def image_to_base64(self, image_path: str) -> str:
        """
        将图片转换为base64编码
        
        Args:
            image_path: 图片路径
        
        Returns:
            base64编码的图片
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"转换图片为base64失败 {image_path}: {e}")
            return ""

    async def select_images_with_vlm(self, paper: Dict[str, Any]) -> List[str]:
        """
        使用VLM选择最具信息量的9张图片
        
        Args:
            paper: 论文数据
        
        Returns:
            选择的图片路径列表
        """
        if not paper.get('image_paths'):
            print(f"论文 {paper['paper_id']} 没有可用的图片")
            return []
        
        # 确保首页图片被选择
        first_page = None
        for img_path in paper['image_paths']:
            if 'page_001' in img_path:
                first_page = img_path
                break
        
        # 如果图片数量少于等于9张，直接返回所有图片
        if len(paper['image_paths']) <= 9:
            selected = paper['image_paths']
            print(f"图片数量较少，选择所有 {len(selected)} 张图片")
            return selected
        
        # 构建图片base64编码（选择前几页进行分析，避免token过多）
        sample_images = paper['image_paths'][:10]  # 只分析前10页以提高效率
        img_base_list = []
        
        for img_path in sample_images:
            base64_img = self.image_to_base64(img_path)
            if base64_img:
                img_base_list.append(f"data:image/jpeg;base64,{base64_img}")
        
        # 将多张图片合并为一个base64字符串（根据您的VLM支持格式调整）
        img_base = "|".join(img_base_list) if img_base_list else ""
        
        prompt = f"""
请从这篇论文的图片中选择9张最具信息量和代表性的图片用于社交媒体分享。

论文信息：
标题：{paper['title']}
领域：{', '.join(paper['categories'])}

选择标准（按重要性排序）：
1. 必须包含首页图片（page_001）
2. 优先选择包含实验图表、结果展示的图片
3. 选择配图丰富、信息量大的页面
4. 避免选择纯文本或公式密集的页面
5. 选择视觉效果好、适合社交媒体展示的图片

请根据以上标准选择9张图片，并返回选择的图片编号（1-10），用逗号分隔。
例如：1,3,5,7,9,2,4,6,8

你的选择：
"""
        
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的图像选择助手，擅长从学术论文中选择最具代表性和信息量的图片。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        print(f"正在为论文《{paper['title']}》选择图片...")
        response = await self.call_vllm_api(messages, img_base=img_base, max_tokens=100)
        
        selected_indices = self.parse_image_selection(response, paper['image_paths'], first_page, len(sample_images))
        selected_images = [paper['image_paths'][i] for i in selected_indices]
        
        print(f"选择了 {len(selected_images)} 张图片")
        return selected_images

    def parse_image_selection(self, response: str, image_paths: List[str], first_page: str, sample_size: int) -> List[int]:
        """
        解析图片选择结果
        
        Args:
            response: VLM响应
            image_paths: 所有图片路径列表
            first_page: 首页图片路径
            sample_size: 分析的样本图片数量
        
        Returns:
            选择的图片索引列表
        """
        selected_indices = []
        
        # 解析响应中的数字
        numbers = re.findall(r'\d+', response)
        if numbers:
            # 将样本选择映射到实际图片索引
            selected_indices = [int(num) - 1 for num in numbers if 1 <= int(num) <= sample_size]
        
        # 如果VLM没有返回有效选择，使用默认策略
        if not selected_indices:
            # 选择前9张图片
            selected_indices = list(range(min(9, len(image_paths))))
        
        # 确保选择9张图片
        if len(selected_indices) > 9:
            selected_indices = selected_indices[:9]
        elif len(selected_indices) < 9:
            # 如果选择不足9张，补充其他图片
            all_indices = list(range(len(image_paths)))
            remaining = [i for i in all_indices if i not in selected_indices]
            selected_indices.extend(remaining[:9 - len(selected_indices)])
        
        # 确保包含首页
        if first_page and first_page in image_paths:
            first_index = image_paths.index(first_page)
            if first_index not in selected_indices:
                # 替换最后一张图片为首页
                selected_indices[-1] = first_index
        
        return selected_indices[:9]  # 确保不超过9张

    async def process_paper_for_xiaohongshu(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        为单篇论文生成小红书内容
        
        Args:
            paper: 论文数据
        
        Returns:
            更新后的论文数据
        """
        print(f"\n正在处理论文: {paper['title']}")
        
        # 生成小红书文案
        xiaohongshu_content = await self.generate_xiaohongshu_content(paper)
        paper['xiaohongshu_content'] = xiaohongshu_content
        
        # 选择图片
        selected_images = await self.select_images_with_vlm(paper)
        paper['selected_images'] = selected_images
        
        print(f"✅ 文案生成完成，选择了 {len(selected_images)} 张图片")
        return paper

    async def process_all_papers(self, json_file_path: str, max_papers: int = None) -> Dict[str, Any]:
        """
        处理所有论文
        
        Args:
            json_file_path: JSON文件路径
            max_papers: 最大处理论文数量
        """
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        processed_count = 0
        total_papers = len(data["papers"])
        
        if max_papers:
            total_papers = min(total_papers, max_papers)
        
        os.makedirs("papers", exist_ok=True)
        
        # 首先下载PDF和转换图片
        for i, paper in enumerate(data["papers"][:total_papers]):
            print(f"\n处理论文 {i+1}/{total_papers}: {paper['title'][:50]}...")
            
            paper_dir = paper["paper_dir"]
            images_dir = os.path.join(paper_dir, "images")
            paper["images_dir"] = images_dir
            
            # 下载PDF
            pdf_path = self.download_pdf(paper["pdf_url"], paper_dir, paper["paper_id"])
            paper["local_pdf_path"] = pdf_path
            
            if pdf_path:
                # 转换为图像
                image_paths = self.pdf_to_images(pdf_path, images_dir, paper["paper_id"])
                paper["image_paths"] = image_paths
                processed_count += 1
        
        # 然后生成小红书内容
        print("\n" + "="*50)
        print("开始生成小红书内容...")
        print("="*50)
        
        # 使用asyncio.gather并发处理论文
        tasks = []
        for i, paper in enumerate(data["papers"][:total_papers]):
            if paper.get('image_paths'):
                tasks.append(self.process_paper_for_xiaohongshu(paper))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 更新数据
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and i < len(data["papers"]):
                data["papers"][i] = result
        
        # 保存结果
        output_file = json_file_path.replace('.json', '_xiaohongshu.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 处理完成！共处理 {processed_count} 篇论文")
        print(f"结果已保存到: {output_file}")
        
        return data

    def print_xiaohongshu_results(self, data: Dict[str, Any]):
        """打印小红书生成结果"""
        print("\n" + "="*60)
        print("小红书内容生成结果")
        print("="*60)
        
        for i, paper in enumerate(data["papers"]):
            if paper.get('xiaohongshu_content'):
                print(f"\n📄 论文 {i+1}: {paper['title']}")
                print(f"🖼️  选择图片: {len(paper.get('selected_images', []))} 张")
                print(f"📝 文案预览: {paper['xiaohongshu_content'][:100]}...")
                print("-" * 40)

# 使用示例
async def main():
    # 初始化处理器
    processor = PaperProcessor()
    
    # 处理MD文件并生成小红书内容
    md_file = "/back-up/lzy/Arxiv_MCP/arxiv_crawler/output_llms/2025-10-15.md"
    output_file = "/back-up/lzy/Arxiv_MCP/arxiv_crawler/output_llms/2025-10-15_with_images.json"
    
    # 解析MD文件
    result = processor.parse_md_to_json(md_file, output_file)
    
    # 处理所有论文（生成小红书内容）
    final_result = await processor.process_all_papers(output_file, max_papers=3)  # 测试时限制3篇
    
    # 打印结果
    processor.print_xiaohongshu_results(final_result)
    
    # 保存单独的小红书内容文件
    xiaohongshu_output = "xiaohongshu_contents.json"
    with open(xiaohongshu_output, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n📖 小红书内容已保存到: {xiaohongshu_output}")

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())