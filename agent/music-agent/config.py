"""
Configuration management for Hakimi Agent.

This module handles API keys and sensitive configuration.
API keys are loaded from a .env file which is NOT committed to git.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration manager for API keys and settings."""

    def __init__(self):
        self.env_file = Path(__file__).parent / ".env"
        self.env_example = Path(__file__).parent / ".env.example"
        self._load_config()

    def _load_config(self):
        """Load configuration from .env file or environment variables."""
        # First try to load from .env file
        if self.env_file.exists():
            self._load_env_file()

        # Fall back to environment variables
        self.ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")
        self.SUNO_API_KEY = os.getenv("SUNO_API_KEY", "")
        self.HF_TOKEN = os.getenv("HF_TOKEN", "")
        self.AIMUSIC_BASE_URL = os.getenv("AIMUSIC_BASE_URL", "https://api.sunoapi.com")
        self.FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

    def _load_env_file(self):
        """Load environment variables from .env file."""
        with open(self.env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

    def ensure_configured(self):
        """
        Ensure all required API keys are configured.
        If not, guide user to create .env file.
        """
        if not self.env_file.exists():
            print("\n[!] 配置文件 .env 不存在")
            print("[*] 正在创建配置文件模板...")
            self._create_env_file()
            print(f"\n[OK] 已创建配置文件：{self.env_file.resolve()}")
            print("\n请编辑 .env 文件，填入你的 API 密钥，然后重新运行程序。")
            print("\n需要配置的密钥：")
            print("  - ZAI_API_KEY: 智谱 AI API 密钥（必需）")
            print("  - SUNO_API_KEY: Suno API 密钥（必需）")
            print("  - HF_TOKEN: Hugging Face Token（可选）")
            return False

        # Check required keys
        missing = []
        if not self.ZAI_API_KEY:
            missing.append("ZAI_API_KEY")
        if not self.SUNO_API_KEY:
            missing.append("SUNO_API_KEY")

        if missing:
            print(f"\n[!] 缺少必需的 API 密钥：{', '.join(missing)}")
            print(f"请编辑 {self.env_file.resolve()} 文件，填入密钥后重新运行。")
            return False

        return True

    def _create_env_file(self):
        """Create .env file from template or scratch."""
        content = """# Hakimi Agent 配置文件
# 请填入你的 API 密钥（不要包含在 git 提交中）

# 智谱 AI API 密钥（必需）- 用于 LLM 提示词生成
ZAI_API_KEY=your_zhipu_ai_api_key_here

# Suno API 密钥（必需）- 用于音乐生成
SUNO_API_KEY=your_suno_api_key_here

# Suno API 基础 URL（可选，默认为官方地址）
AIMUSIC_BASE_URL=https://api.sunoapi.com

# Hugging Face Token（可选）- 仅在使用 HF MusicGen 时需要
# HF_TOKEN=your_huggingface_token_here

# ffmpeg binary path (optional). Set to directory or executable path if ffmpeg isn't on PATH
FFMPEG_PATH=ffmpeg
"""
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write(content)


# Global config instance
config = Config()


# Convenience functions
def get_zai_api_key() -> str:
    """Get ZhipuAI API key."""
    return config.ZAI_API_KEY


def get_suno_api_key() -> str:
    """Get Suno API key."""
    return config.SUNO_API_KEY


def get_hf_token() -> Optional[str]:
    """Get Hugging Face token."""
    return config.HF_TOKEN if config.HF_TOKEN else None


def get_aimusic_base_url() -> str:
    """Get AI Music API base URL."""
    return config.AIMUSIC_BASE_URL


def get_ffmpeg_path() -> str:
    """Get ffmpeg binary path or command."""
    return config.FFMPEG_PATH or "ffmpeg"


if __name__ == "__main__":
    # Test configuration
    print("=== 配置测试 ===")
    if config.ensure_configured():
        print("\n[OK] 配置检查通过")
        print(f"ZAI_API_KEY: {'*' * 10}{config.ZAI_API_KEY[-4:] if len(config.ZAI_API_KEY) > 4 else '未设置'}")
        print(f"SUNO_API_KEY: {'*' * 10}{config.SUNO_API_KEY[-4:] if len(config.SUNO_API_KEY) > 4 else '未设置'}")
        print(f"AIMUSIC_BASE_URL: {config.AIMUSIC_BASE_URL}")
    else:
        print("\n[ERROR] 配置检查失败，请按照提示配置后重试")
