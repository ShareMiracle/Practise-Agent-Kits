# arXiv论文爬取工具

一个用于爬取arXiv预印本论文的Python脚本，支持自定义搜索关键词、批量爬取、自动下载PDF并保存结果到CSV文件。

## 功能特性

- 🔍 **精准搜索**：支持自定义搜索关键词，默认搜索医学影像配准领域
- 📥 **自动下载**：自动下载论文PDF文件并保存到指定目录
- 📊 **结果记录**：将爬取结果保存到CSV文件，包含论文来源、ID、标题、作者、PDF链接等信息
- 🛡️ **反爬机制**：
  - 随机User-Agent
  - 随机请求延迟
  - 分块下载大文件
  - 失败重试机制
- ✅ **PDF验证**：自动验证下载的PDF文件有效性
- 📚 **批量爬取**：支持一次性爬取多个主题
- 🎯 **领域筛选**：默认筛选计算机视觉(cs.CV)和医学物理(physics.med-ph)领域

## 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <项目地址>
   cd clawer__arxiv
   ```

2. **安装依赖**
   脚本会自动检查并安装所需依赖：
   - requests
   - fake_useragent
   - beautifulsoup4

## 使用方法

### 基本使用

默认爬取"medical image registration"主题的论文：

```bash
python clawer.py
```

### 自定义爬取数量

使用`-n`或`--num`参数指定爬取的论文数量：

```bash
python clawer.py -n 10
```

### 批量爬取多个主题

修改脚本中的`batch_crawl`函数调用，传入主题列表：

```python
if __name__ == "__main__":
    # ... 其他代码 ...
    
    # 批量爬取示例
    topics = ["medical image registration", "computer vision", "deep learning"]
    batch_crawl(topics)
```

### 自定义搜索主题

调用`set_search_phrase`函数设置自定义主题：

```python
if __name__ == "__main__":
    # ... 其他代码 ...
    
    # 设置自定义主题
    set_search_phrase("deep learning for medical images")
    multi_source_crawl(max_results=args.num)
```

## 项目结构

```
clawer__arxiv/
├── clawer.py          # 主爬取脚本
├── multi_source_pdfs/ # PDF文件保存目录
│   └── <主题名>/      # 按主题分类的PDF文件
└── multi_source_papers_<主题名>.csv # 爬取结果CSV文件
```

## 配置说明

脚本中的全局配置参数：

- `DEFAULT_SEARCH_PHRASE`: 默认搜索关键词
- `MAX_RESULTS_PER_SITE`: 每个来源的最大爬取结果数
- `BASE_PDF_SAVE_DIR`: PDF保存基础目录
- `BASE_CSV_PATH`: 结果记录CSV基础路径
- `REQUEST_DELAY`: 随机请求延迟范围（秒）
- `DOWNLOAD_RETRIES`: 下载失败重试次数
- `TIMEOUT`: 超时时间（秒）

## 爬取来源

- **arXiv**: 预印本平台，无权限限制

## 注意事项

1. 请遵守arXiv的使用条款和爬虫政策
2. 不要设置过短的请求延迟，以免给服务器带来过大压力
3. 建议合理控制爬取数量，避免滥用
4. 部分论文可能无法下载，会在CSV文件中标记为"失败"

## 依赖库

- `requests`: 用于发送HTTP请求
- `fake_useragent`: 生成随机User-Agent
- `beautifulsoup4`: HTML解析
- `xml.etree.ElementTree`: XML解析
- `csv`: CSV文件操作
- `os`: 文件系统操作
- `random`: 生成随机数
- `re`: 正则表达式
- `time`: 时间操作

## 许可证

MIT License
