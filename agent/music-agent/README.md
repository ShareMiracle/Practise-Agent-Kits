# README.md
## Quick Start

### First Time Setup

1. **Configure API Keys**:
```bash
# Run this to create .env file template
python config.py
```
Then edit `.env` file and fill in your API keys:
- `ZAI_API_KEY`: Your Zhipu AI API key (required)
- `SUNO_API_KEY`: Your Suno API key (required)

2. **Run the Agent**:
```bash
python agent.py
```

### Test Individual Modules
```bash
python -m crawler.hakimi_crawler          # Run web crawler
python -m middleware.suno_client          # Test music generation
python -m publisher.bilibili_playwright   # Test Bilibili upload
```

## Project Overview

This is a **Hakimi meme music generation and auto-upload agent** that creates Japanese-style meme music based on Chinese user input and automatically publishes it to Bilibili. The pipeline consists of:

1. **Web crawler** → Collects "Hakimi" meme content from Chinese websites
2. **LLM middleware** → Converts Chinese user requirements to English music prompts using corpus knowledge
3. **Music generation** → Uses Suno API to generate music from prompts
4. **Video rendering** → Combines audio with static cover image using ffmpeg
5. **Auto-upload** → Uses Playwright + pyautogui to automatically upload to Bilibili

## Project Structure

The project is organized into three main modules:

### `agent.py` (Main Entry Point)
The orchestrator that connects all components:
- Takes Chinese user input
- Calls `middleware.generate_music_prompt()` to get English prompt + style tags
- Calls `middleware.generate_music_from_prompt_en()` to generate music
- Calls `middleware.audio_to_video()` to create MP4 from audio + cover.jpg
- Calls `publisher.publish_to_bilibili()` to auto-upload

### `crawler/` - Web Scraping Module
- `hakimi_crawler.py`: BFS crawler to collect Hakimi meme corpus from web

### `middleware/` - Content Generation Module
- `hakimi_middleware.py`: LLM-based prompt generation
- `suno_client.py`: Suno API client for music generation
- `render_video.py`: Video rendering with ffmpeg

### `publisher/` - Platform Publishing Module
- `bilibili_playwright.py`: Automated Bilibili upload
- `screen_click_upload.py`: Screen automation utilities

### Output Directories
- `output/music/`: All generated music files (Suno, MusicGen)
- `output/video/`: All generated video files
- `output/corpus/`: Web crawler data
- `covers/`: Cover images for videos
- `templates/`: UI template images for screen matching
- `playwright_bili_profile/`: Persistent browser session data

All output directories are created automatically when needed.

### Import Conventions

When working with this codebase:
- Main entry point: `python agent.py`
- Import from modules: `from middleware.suno_client import generate_music_from_prompt_en`
- Run modules directly: `python -m middleware.suno_client`
- Each module has an `__init__.py` that exports main functions

## Core Architecture

### LLM Middleware (middleware/hakimi_middleware.py)
Depends on custom `zai` module (ZhipuAiClient) for Chinese LLM integration:
- Loads random Hakimi corpus snippets from `output/corpus/hakimi_corpus.jsonl`
- Constructs prompt for LLM to generate structured JSON output
- Returns: `{music_prompt_en, music_prompt_zh, style_tags, use_lyrics, lyrics_zh}`
- **Configuration**: Reads `ZAI_API_KEY` from `config.py`

### Music Generation

**Suno Client (middleware/suno_client.py)** - Primary method:
- Uses AI Music API (https://api.sunoapi.com) to generate music
- **Configuration**: Reads `SUNO_API_KEY` and `AIMUSIC_BASE_URL` from `config.py`
- Creates task → polls until complete → downloads MP3 to `output/music/` directory
- Uses description mode (custom_mode=False) with chirp-v4 model

**Alternative: Local MusicGen** - Not used in main pipeline (if implemented):
- Uses local Transformers model from `models/musicgen/`
- Loads on CUDA if available, else CPU
- Generates shorter clips (10s default), outputs WAV format to `output/music/`

**Hugging Face Client** - Not used in main pipeline (if implemented):
- Uses HF Inference API, requires `HF_TOKEN` environment variable
- Outputs WAV files to `output/music/` directory

### Bilibili Auto-Upload (publisher/bilibili_playwright.py)

Hybrid approach using both Playwright and GUI automation:

**Playwright handles**:
- Persistent browser session (saves login state in `playwright_bili_profile/`)
- Opens upload page: https://member.bilibili.com/platform/upload/video/frame
- Checks login status and prompts manual login if needed

**pyautogui + OpenCV handles**:
- Template matching to find upload button (`upload_button.png`)
- Clicks upload button on screen
- Pastes video file path into system file dialog using clipboard
- Scrolls down page to find and click submit button (`submit_button.png`)

**Critical dependencies**: Template images must match UI at current screen resolution

### Video Rendering (middleware/render_video.py)
Simple ffmpeg wrapper:
- Combines static image + audio → MP4
- Default output location: `output/video/hakimi_video.mp4`
- Ensures even dimensions with scale filter: `scale=trunc(iw/2)*2:trunc(ih/2)*2`
- Uses libx264 codec, AAC audio at 192k
- Automatically creates output directory if it doesn't exist

### Web Crawler (crawler/hakimi_crawler.py)
BFS crawler to build Hakimi meme corpus:
- Crawls allowed domains (bilibili.com, zhihu.com, etc.)
- Extracts sentences containing keywords: "哈基米", "哈吉米", "hachimi"
- Saves to `output/corpus/hakimi_corpus.jsonl` in format: `{url, text, keywords}`
- Respects rate limits (1-3s sleep between requests)

## Common Development Commands

### Run the full pipeline
```bash
python agent.py
```
Interactive CLI that will:
1. Prompt for Chinese music requirements
2. Generate music via Suno
3. Render video with cover.jpg
4. Auto-upload to Bilibili (requires manual login on first run)

### Test individual components

**Test LLM middleware only**:
```bash
python -m middleware.hakimi_middleware
```
Requires: `ZAI_API_KEY` environment variable

**Test Suno music generation**:
```bash
python -m middleware.suno_client
```
Outputs to `output/music/` directory

**Test video rendering**:
```bash
python -m middleware.render_video
```
Requires: `output/music/hakimi_aimusicapi_test.mp3` and `covers/cover.jpg`
Outputs to: `output/video/hakimi_video.mp4`

**Test Bilibili upload**:
```bash
python -m publisher.bilibili_playwright
```
Requires: `output/video/hakimi_video.mp4`, `covers/cover.jpg`, `templates/upload_button.png`, `templates/submit_button.png`

**Run web crawler**:
```bash
python -m crawler.hakimi_crawler
```
Update `SEED_URLS` before running. Output: `output/corpus/hakimi_corpus.jsonl`

## Environment Setup

### Configuration Management

The project uses a centralized configuration system via `config.py` to manage API keys and sensitive information.

**Configuration Files**:
- `.env` - Contains actual API keys (NOT committed to git)
- `.env.example` - Template file (committed to git)
- `.gitignore` - Ensures `.env` is never committed

**First Time Setup**:
1. Run `python config.py` to create `.env` template
2. Edit `.env` and fill in your API keys
3. Run `python agent.py` - it will automatically check configuration

**Required API Keys**:
- `ZAI_API_KEY`: Zhipu AI API key for LLM prompt generation (required)
  - Get it at: https://open.bigmodel.cn/
- `SUNO_API_KEY`: Suno API key for music generation (required)
  - Get it at: https://sunoapi.com/

**Optional Configuration**:
- `HF_TOKEN`: Hugging Face token (only if using HF MusicGen)
- `AIMUSIC_BASE_URL`: Override Suno API base URL (default: https://api.sunoapi.com)

### Required Files
- `covers/cover.jpg`: Cover image for video (16:9 recommended, e.g., 1920x1080)
- `output/corpus/hakimi_corpus.jsonl`: Meme corpus (generated by crawler or provided)
- `templates/upload_button.png`: Template for Bilibili upload button
- `templates/submit_button.png`: Template for Bilibili submit button
- `models/musicgen/`: Local MusicGen model files (if using local generation)

### Key Dependencies
- `playwright`: Browser automation (requires `playwright install chromium`)
- `pyautogui`, `pyperclip`: GUI automation
- `opencv-python` (cv2): Template matching
- `transformers`, `torch`, `scipy`: For local MusicGen
- `requests`: API calls
- `beautifulsoup4`: Web scraping
- Custom module: `zai` (ZhipuAiClient) - not in standard libraries

## Important Notes

### Screen Automation Caveats
The Bilibili upload process uses template matching which is fragile:
- Template images must match current UI theme/language
- Screen resolution and DPI scaling affect matching
- Browser zoom level must be 100%
- If template matching fails, manual intervention is required

### File Paths
All file operations use `Path().resolve()` to get absolute paths. When debugging file-not-found errors, check:
- Working directory is project root
- `covers/cover.jpg` exists
- `templates/upload_button.png` and `templates/submit_button.png` exist
- Generated files are in expected locations:
  - Music files: `output/music/`
  - Video files: `output/video/`
  - Corpus data: `output/corpus/`

### Bilibili Login
First run requires manual login:
- Browser opens in non-headless mode
- Login state persists in `playwright_bili_profile/`
- Subsequent runs reuse saved session

### Music Generation Timing
Suno API polling:
- Default timeout: 360 seconds (6 minutes)
- Poll interval: 15 seconds
- Adjust `max_wait` and `interval` parameters if needed

### Security Notes

**API Keys Management**:
- All API keys are managed through `config.py` and `.env` file
- `.env` file is automatically ignored by git (via `.gitignore`)
- Never commit `.env` file or hardcode API keys in source code
- Use `.env.example` as a template for others to set up their environment
