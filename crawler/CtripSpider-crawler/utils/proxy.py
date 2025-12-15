# -*- coding = utf-8 -*-
# @Time :2023/7/13 21:11
# @Author :小岳
# @Email  :401208941@qq.com
# @PROJECT_NAME :scenic_spots_comment
# @File :  proxy.py
import requests
from config import IS_PROXY

def my_get_proxy() -> dict:
    """
    使用 Clash Verge 代理（端口7890）
    如果IS_PROXY为False，则返回空字典（不使用代理）
    """
    if IS_PROXY:
        # 使用你的 Clash 配置（端口7890）
        clash_proxy = {
            "http": "http://127.0.0.1:7897",
            "https": "http://127.0.0.1:7897"
        }
        return clash_proxy
    else:
        return {}