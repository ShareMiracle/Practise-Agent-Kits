# Publishers 模块说明

该目录包含项目对外发布组件，当前核心聚焦小红书与 Twitter：

- `xiaohongshu_selenium_publisher.py`：基于 Selenium 的真实图文发布自动化。
- `xiaohongshu_publisher.py`：面向 API 研究/离线调试的占位实现（不执行真实发布）。
- `twitter_publisher.py`：基于 Tweepy 的 Twitter/Twitter X 发布器，支持单条推文与线程。

## 依赖与环境变量

| 组件 | 主要依赖 | 必需环境变量 |
| --- | --- | --- |
| 小红书 Selenium | `selenium`, `webdriver-manager`, 本地 Chrome/Chromedriver | `XIAOHONGSHU_COOKIE`（完整 `document.cookie` 字符串）|
| 小红书 API（占位） | `requests` | `XIAOHONGSHU_COOKIE`, `XIAOHONGSHU_A1`, `XIAOHONGSHU_WEB_SESSION` |
| Twitter Publisher | `tweepy` | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`, `TWITTER_BEARER_TOKEN` |


安装依赖：

```bash
pip install -r requirements.txt
```

## XiaohongshuSeleniumPublisher

特点：

- 自动加载 `XIAOHONGSHU_COOKIE`，进入 `https://creator.xiaohongshu.com/publish/publish`。
- 逐步执行“填写标题 → 填写正文 → 一键排版 → 预览下一步 → 发布”。
- 在按钮无法定位时提示人工兜底，并延迟 2 分钟关闭浏览器方便检查。

使用方式：

```python
from publishers.xiaohongshu_selenium_publisher import XiaohongshuSeleniumPublisher
from config import settings

publisher = XiaohongshuSeleniumPublisher(cookie=settings.XIAOHONGSHU_COOKIE)
note_id = publisher.publish_note(
    title="AI 周报",
    content="这里是正文...",
    tags=["AI", "研究"]
)
print("note id:", note_id)
```

调试脚本：

```bash
python publishers/xiaohongshu_selenium_publisher.py
```

常见要求：

1. 先在浏览器完成一次人工登录并复制 `document.cookie` 到 `.env`。
2. 保持 Chrome 与 Chromedriver 版本匹配（`webdriver-manager` 会自动拉取最新驱动）。
3. 如遇按钮文字变化，可在文件顶部的 `*_BUTTON_TEXTS` 中新增关键字。

## XiaohongshuPublisher（占位实现）

供研究 API 或离线测试使用，默认不会真正发文，而是记录日志并返回假 ID。如要对接真实 API，可在 `publish_note` 中补充抓包得到的请求。

## TwitterPublisher

功能：

- `post_tweet`：发布单条推文，可附带图片/视频（使用 v1.1 媒体上传）。
- `post_thread`：串推，自动引用上一条 Tweet ID。
- `delete_tweet`：删除指定推文。
- 内置 429 限流重试（指数退避 + `x-rate-limit-reset` 推算）。

示例：

```python
from publishers.twitter_publisher import TwitterPublisher
from config import settings

publisher = TwitterPublisher(
    api_key=settings.TWITTER_API_KEY,
    api_secret=settings.TWITTER_API_SECRET,
    access_token=settings.TWITTER_ACCESS_TOKEN,
    access_secret=settings.TWITTER_ACCESS_SECRET,
    bearer_token=settings.TWITTER_BEARER_TOKEN,
)
publisher.post_tweet("Hello Twitter!")
```

## 目录结构

```
publishers/
├── README.md              # 本文件
├── __init__.py            # 导出所有 publisher 类
├── twitter_publisher.py
├── xiaohongshu_publisher.py
└── xiaohongshu_selenium_publisher.py
```

## 开发与调试建议

1. **日志**：所有发布器均使用 `utils.logger` 输出结构化日志，默认写入 `logs/`。
2. **配置**：统一通过 `.env` + `config.settings` 注入。
3. **测试**：
   - Twitter：可使用 `python test_twitter_credentials.py` 验证凭证。
   - Xiaohongshu：`python test_xiaohongshu_cookie.py` 检测 Cookie 是否生效。
4. **扩展**：如需新增平台，只需在本目录添加新的 `Publisher` 类，并在 `publishers/__init__.py` 导出即可供 `agents` 使用。
