
import os
import requests
import time
import re
from urllib.parse import quote, urlencode
import json
import random
import hashlib
import brotli
import gzip
import zlib
from fake_useragent import UserAgent
import shutil

class BaiduImageSpider:
    def __init__(self):
        # 使用fake-useragent生成随机User-Agent
        self.ua = UserAgent()
        self.session = requests.Session()
        self.update_headers()
        
    def update_headers(self):
        """更新请求头"""
        self.headers = {
            'User-Agent': self.ua.random,
            'Referer': 'https://image.baidu.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0',
        }
        self.session.headers.update(self.headers)
    
    def search_images(self, keyword, num=50, folder_path='./baidu_images'):
        """
        搜索并下载百度图片
        
        Args:
            keyword: 搜索关键词
            num: 下载图片数量
            folder_path: 保存图片的文件夹路径
        """
        
        # 创建保存图片的文件夹
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"已创建文件夹: {folder_path}")
        
        downloaded_count = 0
        page_num = 0
        start_time = time.time()
        max_failed_attempts = 3
        
        print(f"开始搜索关键词: {keyword}")
        print(f"目标下载数量: {num}张")
        print(f"保存路径: {folder_path}")
        print("-" * 50)
        
        while downloaded_count < num:
            # 每5次请求更换一次User-Agent
            if page_num % 5 == 0:
                self.update_headers()
            
            try:
                # 方法1：尝试使用新的接口格式
                images = self.fetch_images_method1(keyword, page_num)
                
                # 如果方法1失败，尝试方法2
                if not images and page_num == 0:
                    print("尝试方法2...")
                    images = self.fetch_images_method2(keyword, page_num)
                
                if not images:
                    print(f"第 {page_num + 1} 页没有获取到图片数据")
                    page_num += 1
                    continue
                
                print(f"第 {page_num + 1} 页获取到 {len(images)} 张图片信息")
                
                # 下载图片
                for img_info in images:
                    if downloaded_count >= num:
                        break
                    
                    img_url = None
                    
                    # 尝试获取图片URL
                    if isinstance(img_info, dict):
                        url_fields = ['thumbURL', 'middleURL', 'hoverURL', 'objURL', 'replaceUrl']
                        for field in url_fields:
                            if field in img_info and img_info[field] and isinstance(img_info[field], str):
                                if img_info[field].startswith('http'):
                                    img_url = img_info[field]
                                    break
                    elif isinstance(img_info, str) and img_info.startswith('http'):
                        img_url = img_info
                    
                    if img_url:
                        if self.download_image(img_url, folder_path, downloaded_count, keyword, downloaded_count):
                            downloaded_count += 1
                            print(f"已下载: {downloaded_count}/{num}")
                            time.sleep(0.5)  # 避免请求过快
                
                page_num += 1
                
                # 每页之间随机等待1-3秒
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"第 {page_num + 1} 页处理失败: {e}")
                page_num += 1
                time.sleep(2)
                continue
        
        end_time = time.time()
        print(f"\n下载完成！")
        print(f"总耗时: {end_time - start_time:.2f}秒")
        print(f"成功下载: {downloaded_count}张图片")
        print(f"图片保存在: {folder_path}")
        
        if downloaded_count < num:
            print(f"注意: 只下载了 {downloaded_count}/{num} 张图片")
    
    def fetch_images_method1(self, keyword, page_num):
        """方法1：使用百度图片搜索页面直接解析"""
        try:
            encoded_keyword = quote(keyword)
            pn = page_num * 30
            
            # 使用百度图片搜索页面
            url = f'https://image.baidu.com/search/index?tn=baiduimage&word={encoded_keyword}&pn={pn}'
            
            response = self.session.get(url, timeout=15)
            
            # 尝试多种解码方式
            content = self.decode_response(response)
            
            # 从HTML中提取图片数据
            images = self.extract_images_from_html(content)
            
            return images
            
        except Exception as e:
            print(f"方法1获取失败: {e}")
            return []
    
    def fetch_images_method2(self, keyword, page_num):
        """方法2：使用百度图片JSON接口"""
        try:
            encoded_keyword = quote(keyword)
            pn = page_num * 30
            
            # 构造JSON接口URL
            params = {
                'tn': 'resultjson_com',
                'ipn': 'rj',
                'ct': '201326592',
                'is': '',
                'fp': 'result',
                'queryWord': keyword,
                'cl': '2',
                'lm': '-1',
                'ie': 'utf-8',
                'oe': 'utf-8',
                'adpicid': '',
                'st': '-1',
                'z': '',
                'ic': '0',
                'hd': '',
                'latest': '',
                'copyright': '',
                'word': keyword,
                's': '',
                'se': '',
                'tab': '',
                'width': '',
                'height': '',
                'face': '0',
                'istype': '2',
                'qc': '',
                'nc': '1',
                'fr': '',
                'expermode': '',
                'force': '',
                'pn': pn,
                'rn': '30',
                'gsm': '1e',
                str(int(time.time() * 1000)): ''
            }
            
            url = 'https://image.baidu.com/search/acjson?' + urlencode(params)
            
            response = self.session.get(url, timeout=15)
            content = self.decode_response(response)
            
            # 尝试解析JSON
            try:
                data = json.loads(content)
                if 'data' in data:
                    # 过滤掉空数据
                    return [img for img in data['data'] if img]
            except:
                # 尝试从字符串中提取JSON
                match = re.search(r'({.*})', content)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        if 'data' in data:
                            return [img for img in data['data'] if img]
                    except:
                        pass
            
            return []
            
        except Exception as e:
            print(f"方法2获取失败: {e}")
            return []
    
    def decode_response(self, response):
        """解码响应内容，处理压缩"""
        # 检查编码
        encoding = response.encoding
        if encoding is None:
            encoding = 'utf-8'
        
        # 检查内容编码
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        
        try:
            if 'br' in content_encoding:
                # Brotli压缩
                content = brotli.decompress(response.content)
                return content.decode('utf-8')
            elif 'gzip' in content_encoding:
                # Gzip压缩
                content = gzip.decompress(response.content)
                return content.decode('utf-8')
            elif 'deflate' in content_encoding:
                # Deflate压缩
                content = zlib.decompress(response.content, -zlib.MAX_WBITS)
                return content.decode('utf-8')
            else:
                # 无压缩或未知压缩
                return response.content.decode(encoding, errors='ignore')
        except:
            # 如果解码失败，尝试直接解码
            try:
                return response.text
            except:
                return response.content.decode('utf-8', errors='ignore')
    
    def extract_images_from_html(self, html_content):
        """从HTML中提取图片信息"""
        images = []
        
        try:
            # 方法1：提取JSON数据
            json_patterns = [
                r'"thumbURL":"(https?:[^"]+)"',
                r'"middleURL":"(https?:[^"]+)"',
                r'"objURL":"(https?:[^"]+)"',
                r'http[s]?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|bmp)'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if match not in images and 'http' in match:
                        images.append(match)
            
            # 方法2：提取base64数据中的图片URL
            base64_pattern = r'"objURL":"([^"]+)"'
            matches = re.findall(base64_pattern, html_content)
            for match in matches:
                if match.startswith('http') and match not in images:
                    images.append(match)
            
            # 去重
            images = list(set(images))
            
        except Exception as e:
            print(f"HTML解析失败: {e}")
        
        return images[:60]  # 限制返回数量
    
    def download_image(self, img_url, folder_path, index, keyword, count):
        """
        下载单张图片
        """
        try:
            # 检查URL是否有效
            if not img_url or 'http' not in img_url:
                return False
            
            # 设置超时时间
            response = self.session.get(img_url, timeout=20, stream=True)
            
            if response.status_code == 200:
                # 获取文件扩展名
                content_type = response.headers.get('content-type', '')
                
                if 'image' not in content_type:
                    # 如果不是图片，跳过
                    return False
                
                # 根据Content-Type确定扩展名
                ext_map = {
                    'image/jpeg': '.jpg',
                    'image/jpg': '.jpg',
                    'image/png': '.png',
                    'image/gif': '.gif',
                    'image/webp': '.webp',
                    'image/bmp': '.bmp'
                }
                
                ext = ext_map.get(content_type.lower())
                
                if not ext:
                    # 从URL中提取扩展名
                    url_lower = img_url.lower()
                    for img_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.jfif']:
                        if img_ext in url_lower:
                            ext = img_ext
                            break
                
                if not ext:
                    ext = '.jpg'  # 默认扩展名
                
                # 清理文件名
                safe_keyword = re.sub(r'[<>:"/\\|?*]', '_', keyword)[:50]
                
                # 生成唯一文件名
                timestamp = int(time.time() * 1000)
                random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                filename = f"{count}{ext}"
                # filename = f"{safe_keyword}_{index+1:03d}_{timestamp}_{random_str}{ext}"
                
                # 保存图片
                file_path = os.path.join(folder_path, filename)
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=10240):
                        if chunk:
                            f.write(chunk)
                
                # 验证文件大小
                file_size = os.path.getsize(file_path)
                if file_size > 1024:  # 大于1KB才认为是有效图片
                    return True
                else:
                    os.remove(file_path)
                    return False
            
            return False
            
        except Exception as e:
            print(f"下载失败 {img_url[:50]}...: {str(e)[:100]}")
            return False


def install_dependencies():
    """安装必要的依赖"""
    import subprocess
    import sys
    
    dependencies = [
        'requests',
        'fake-useragent',
        'brotli'
    ]
    
    print("正在检查并安装依赖包...")
    for package in dependencies:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"正在安装 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} 安装完成")


def main():
    # 安装依赖
    install_dependencies()
    
    # 创建爬虫实例
    spider = BaiduImageSpider()
    
    print("=" * 60)
    print("百度图片下载器 v2.0")
    print("=" * 60)
    
    # 用户输入
    keyword = input("请输入搜索关键词: ").strip()
    if not keyword:
        keyword = "长沙美食"
        print(f"使用默认关键词: {keyword}")
    
    # 设置下载数量
    while True:
        try:
            num_input = input("请输入要下载的图片数量 (默认50张): ").strip()
            if num_input == "":
                num = 50
                break
            num = int(num_input)
            if num > 0 and num <= 200:
                break
            elif num > 200:
                print("数量过大，建议不超过200张")
            else:
                print("请输入大于0的数字！")
        except ValueError:
            print("请输入有效的数字！")
    
    # 设置保存路径
    folder_path = input("请输入保存图片的文件夹路径 (默认: ./baidu_images): ").strip()
    if folder_path == "":
        folder_path = "./baidu_images"
    
    # 开始爬取
    print("\n开始爬取...")
    print("=" * 60)
    
    try:
        spider.search_images(keyword, num, folder_path)
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"程序出错: {e}")
    
    input("\n按Enter键退出...")


# 演示模式
def run_demo():
    """演示函数，可以直接运行"""
    print("=" * 60)
    print("百度图片下载器 - 演示模式")
    print("=" * 60)
    
    # 安装依赖
    install_dependencies()
    
    spider = BaiduImageSpider()
    
    # 设置参数
    keyword = "长沙美食"
    num = 50
    folder_path = "./baidu_images"
    
    # 创建文件夹
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    print(f"\n开始爬取: {keyword}")
    print(f"目标数量: {num}张")
    print(f"保存路径: {folder_path}")
    print("=" * 60)
    
    spider.search_images(keyword, num, folder_path)

def recreate_folder(folder_path):
    """
    检查文件夹是否存在，如果存在则删除并创建新的空文件夹
    
    Args:
        folder_path: 要操作的文件夹路径
    """
    try:
        # 检查文件夹是否存在
        if os.path.exists(folder_path):
            print(f"文件夹 '{folder_path}' 存在，正在删除...")
            
            # 删除文件夹（包括其中的所有内容）
            shutil.rmtree(folder_path)
            print(f"文件夹 '{folder_path}' 已删除")
        else:
            print(f"文件夹 '{folder_path}' 不存在")
        
        # 创建新的文件夹
        os.makedirs(folder_path, exist_ok=True)
        print(f"已创建新的文件夹 '{folder_path}'")
        
        return True
        
    except Exception as e:
        print(f"操作失败: {e}")


# def spider_from_web(keyword, num=5):
#     spider = BaiduImageSpider()
    
#     # 设置参数
#     # folder_path = "./baidu_images"
#     folder_path = "D:/projects/baidu_downloader/web_spider_image/tmp"
#     recreate_folder(folder_path)
    
#     print(f"\n开始爬取: {keyword}")
#     print(f"目标数量: {num}张")
#     print(f"保存路径: {folder_path}")
#     print("=" * 60)
    
#     spider.search_images(keyword, num, folder_path)

def spider_from_web(folder_path, keyword, num=5):
    spider = BaiduImageSpider()
    
    # 设置参数
    # folder_path = "./baidu_images"
    # folder_path = "D:/projects/baidu_downloader/web_spider_image/tmp"
    recreate_folder(folder_path)
    
    print(f"\n开始爬取: {keyword}")
    print(f"目标数量: {num}张")
    print(f"保存路径: {folder_path}")
    print("=" * 60)
    
    spider.search_images(keyword, num, folder_path)


if __name__ == "__main__":
    spider_from_web("长沙美食", 2)