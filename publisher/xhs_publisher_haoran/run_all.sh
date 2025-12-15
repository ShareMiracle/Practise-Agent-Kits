#!/usr/bin/env bash
set -e

# 切到脚本所在目录，保证相对路径一致
cd "$(dirname "$0")"

# 建议使用你自己的 Python 环境命令，比如 python / python3 / venv 里的 python
python run_full_pipeline.py
