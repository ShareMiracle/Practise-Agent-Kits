# -*- coding = utf-8 -*-
# @Time :2023/7/13 21:32
# @Author :小岳
# @Email  :401208941@qq.com
# @PROJECT_NAME :scenic_spots_comment
# @File :  fake_user_agent.py
from fake_useragent import UserAgent
import random
from config import IS_FAKE_USER_AGENT


def get_fake_user_agent(ua_type: str, default=True) -> str:
    """
    获取伪装的User-Agent
    
    Args:
        ua_type: 类型，mobile或pc
        default: 是否使用默认值
    
    Returns:
        User-Agent字符串
    """
    match ua_type:
        case "mobile":
            if IS_FAKE_USER_AGENT and default:
                return get_mobile_user_agent()
            else:
                return "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36 Edg/114.0.0.0"
        case "pc":
            if IS_FAKE_USER_AGENT and default:
                return get_pc_user_agent()
            else:
                return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36"
        case "wechat":
            return get_wechat_user_agent()
        case "alipay":
            return get_alipay_user_agent()
        case "douyin":
            return get_douyin_user_agent()
        case _:
            return get_mobile_user_agent()  # 默认返回移动端


def get_mobile_user_agent() -> str:
    """生成移动端User-Agent"""
    platforms = [
        # Apple iPhone
        'iPhone; CPU iPhone OS 14_0 like Mac OS X',
        'iPhone; CPU iPhone OS 14_1 like Mac OS X',
        'iPhone; CPU iPhone OS 14_2 like Mac OS X',
        'iPhone; CPU iPhone OS 14_3 like Mac OS X',
        'iPhone; CPU iPhone OS 14_4 like Mac OS X',
        'iPhone; CPU iPhone OS 14_5 like Mac OS X',
        'iPhone; CPU iPhone OS 14_6 like Mac OS X',
        'iPhone; CPU iPhone OS 14_7 like Mac OS X',
        'iPhone; CPU iPhone OS 14_8 like Mac OS X',
        'iPhone; CPU iPhone OS 15_0 like Mac OS X',
        'iPhone; CPU iPhone OS 15_1 like Mac OS X',
        'iPhone; CPU iPhone OS 15_2 like Mac OS X',
        'iPhone; CPU iPhone OS 15_3 like Mac OS X',
        'iPhone; CPU iPhone OS 15_4 like Mac OS X',
        'iPhone; CPU iPhone OS 15_5 like Mac OS X',
        'iPhone; CPU iPhone OS 15_6 like Mac OS X',
        'iPhone; CPU iPhone OS 15_7 like Mac OS X',
        'iPhone; CPU iPhone OS 16_0 like Mac OS X',
        'iPhone; CPU iPhone OS 16_1 like Mac OS X',
        'iPhone; CPU iPhone OS 16_2 like Mac OS X',
        
        # Apple iPad
        'iPad; CPU OS 14_0 like Mac OS X',
        'iPad; CPU OS 14_1 like Mac OS X',
        'iPad; CPU OS 14_2 like Mac OS X',
        'iPad; CPU OS 14_3 like Mac OS X',
        'iPad; CPU OS 14_4 like Mac OS X',
        'iPad; CPU OS 14_5 like Mac OS X',
        'iPad; CPU OS 14_6 like Mac OS X',
        'iPad; CPU OS 14_7 like Mac OS X',
        'iPad; CPU OS 15_0 like Mac OS X',
        'iPad; CPU OS 15_1 like Mac OS X',
        'iPad; CPU OS 15_2 like Mac OS X',
        'iPad; CPU OS 15_3 like Mac OS X',
        'iPad; CPU OS 15_4 like Mac OS X',
        'iPad; CPU OS 15_5 like Mac OS X',
        'iPad; CPU OS 15_6 like Mac OS X',
        'iPad; CPU OS 15_7 like Mac OS X',
        'iPad; CPU OS 16_0 like Mac OS X',
        'iPad; CPU OS 16_1 like Mac OS X',
        
        # Google Pixel
        'Linux; Android 8.0.0; Pixel 2 Build/OPD1.170816.004',
        'Linux; Android 8.1.0; Pixel 2 Build/OPM1.171019.021',
        'Linux; Android 9; Pixel 2 Build/PQ1A.190105.004',
        'Linux; Android 10; Pixel 2 Build/QD1A.190821.014',
        'Linux; Android 8.0.0; Pixel XL Build/OPD1.170816.004',
        'Linux; Android 8.1.0; Pixel XL Build/OPM1.171019.021',
        'Linux; Android 9; Pixel 3 Build/PQ1A.190105.004',
        'Linux; Android 10; Pixel 3 Build/QD1A.190821.014',
        'Linux; Android 11; Pixel 3 Build/RD1A.201105.003',
        'Linux; Android 12; Pixel 3 Build/SP1A.210812.016',
        'Linux; Android 9; Pixel 3a Build/PQ2A.190405.003',
        'Linux; Android 10; Pixel 3a Build/QD1A.190821.014',
        'Linux; Android 11; Pixel 3a Build/RD1A.201105.003',
        'Linux; Android 12; Pixel 3a Build/SP1A.210812.016',
        'Linux; Android 10; Pixel 4 Build/QD1A.190821.014',
        'Linux; Android 11; Pixel 4 Build/RD1A.201105.003',
        'Linux; Android 12; Pixel 4 Build/SP1A.210812.016',
        'Linux; Android 11; Pixel 4a Build/RD1A.201105.003',
        'Linux; Android 12; Pixel 4a Build/SP1A.210812.016',
        'Linux; Android 11; Pixel 5 Build/RD1A.201105.003',
        'Linux; Android 12; Pixel 5 Build/SP1A.210812.016',
        'Linux; Android 12; Pixel 6 Build/SP1A.210812.016',
        'Linux; Android 13; Pixel 6 Build/TP1A.220624.014',
        
        # Samsung Galaxy S系列
        'Linux; Android 8.0.0; SM-G950F Build/R16NW',  # Galaxy S8
        'Linux; Android 9; SM-G960F Build/PPR1.180610.011',  # Galaxy S9
        'Linux; Android 10; SM-G970F Build/QP1A.190711.020',  # Galaxy S10e
        'Linux; Android 10; SM-G973F Build/QP1A.190711.020',  # Galaxy S10
        'Linux; Android 10; SM-G975F Build/QP1A.190711.020',  # Galaxy S10+
        'Linux; Android 11; SM-G980F Build/RP1A.200720.012',  # Galaxy S20
        'Linux; Android 11; SM-G981B Build/RP1A.200720.012',  # Galaxy S20 5G
        'Linux; Android 12; SM-G991B Build/SP1A.210812.016',  # Galaxy S21
        'Linux; Android 12; SM-G996B Build/SP1A.210812.016',  # Galaxy S21+
        'Linux; Android 12; SM-G998B Build/SP1A.210812.016',  # Galaxy S21 Ultra
        'Linux; Android 13; SM-S901B Build/TP1A.220624.014',  # Galaxy S22
        'Linux; Android 13; SM-S906B Build/TP1A.220624.014',  # Galaxy S22+
        'Linux; Android 13; SM-S908B Build/TP1A.220624.014',  # Galaxy S22 Ultra'
    ]

    browsers_config = {
        'Chrome': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36',
            'version_range': (70, 110)
        },
        'Firefox': {
            'template': 'Mozilla/5.0 ({platform}; rv:{version}.0) Gecko/20100101 Firefox/{version}.0',
            'version_range': (60, 100)
        },
        'Safari': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version}.0 Mobile/15E148 Safari/604.1',
            'version_range': (10, 16)
        },
        'Opera': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Mobile Safari/537.36 OPR/{version}',
            'version_range': (60, 80)
        },
        'Edge': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Mobile Safari/537.36 Edg/{version}',
            'version_range': (80, 110)
        },
        'UCBrowser': {
            'template': 'Mozilla/5.0 ({platform}) UCBrowser/{version} Safari/537.36',
            'version_range': (12, 15)
        },
        'SamsungBrowser': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/{version} Chrome/{chrome_version} Mobile Safari/537.36',
            'version_range': (10, 18)
        },
        'QQBrowser': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_version} Mobile Safari/537.36 V1_AND_SQ_8.8.68_2538_YYB_D QQ/{version}',
            'version_range': (8, 9)
        },
        'Baidu Browser': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_version} Mobile Safari/537.36 T7/11.0 baidubrowser/{version}',
            'version_range': (10, 15)
        },
        'Quark': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_version} Mobile Safari/537.36 Quark/{version}',
            'version_range': (3, 5)
        },
        'MiuiBrowser': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_version} Mobile Safari/537.36 XiaoMi/MiuiBrowser/{version}',
            'version_range': (10, 15)
        }
    }

    # 常用浏览器列表
    common_browsers = ['Chrome', 'Safari', 'Firefox', 'Edge', 'QQBrowser', 'Baidu Browser', 'UCBrowser']
    
    platform = random.choice(platforms)
    browser = random.choice(common_browsers)
    
    if browser in browsers_config:
        config = browsers_config[browser]
        version = random.randint(*config['version_range'])
        chrome_version = f"{random.randint(70, 110)}.0.{random.randint(1000, 6000)}.{random.randint(100, 200)}"
        
        ua = config['template'].format(
            platform=platform,
            version=version,
            chrome_version=chrome_version
        )
        return ua
    
    # 默认返回Chrome
    version = random.randint(70, 110)
    return f'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.{random.randint(1000, 6000)}.{random.randint(100, 200)} Mobile Safari/537.36'


def get_pc_user_agent() -> str:
    """生成PC端User-Agent"""
    platforms = [
        'Windows NT 10.0; Win64; x64',
        'Windows NT 6.1; Win64; x64', 
        'Windows NT 6.3; Win64; x64',
        'Macintosh; Intel Mac OS X 10_15_7',
        'Macintosh; Intel Mac OS X 10_12_6',
        'Macintosh; Intel Mac OS X 10_14_6',
        'X11; Linux x86_64',
        'X11; Ubuntu; Linux x86_64',
        'X11; Fedora; Linux x86_64',
        'X11; Debian; Linux x86_64'
    ]

    browsers_config = {
        'Chrome': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36',
            'version_range': (70, 110)
        },
        'Firefox': {
            'template': 'Mozilla/5.0 ({platform}; rv:{version}.0) Gecko/20100101 Firefox/{version}.0',
            'version_range': (60, 100)
        },
        'Safari': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version}.0 Safari/605.1.15',
            'version_range': (10, 16)
        },
        'Edge': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36 Edg/{version}',
            'version_range': (80, 110)
        },
        'Opera': {
            'template': 'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36 OPR/{version}',
            'version_range': (60, 80)
        }
    }

    platform = random.choice(platforms)
    browser = random.choice(list(browsers_config.keys()))
    
    config = browsers_config[browser]
    version = random.randint(*config['version_range'])
    chrome_version = f"{random.randint(70, 110)}.0.{random.randint(1000, 6000)}.{random.randint(100, 200)}"
    
    ua = config['template'].format(
        platform=platform,
        version=version,
        chrome_version=chrome_version
    )
    return ua


def get_wechat_user_agent() -> str:
    """生成微信内置浏览器User-Agent"""
    wechat_versions = [
        '7.0.12', '7.0.13', '7.0.14', '7.0.15', '7.0.16', '7.0.17', '7.0.18', 
        '7.0.19', '7.0.20', '7.0.21', '7.0.22', '7.0.23', '8.0.0', '8.0.1',
        '8.0.2', '8.0.3', '8.0.4', '8.0.5', '8.0.6', '8.0.7', '8.0.8'
    ]
    
    platforms = [
        'iPhone; CPU iPhone OS 14_6 like Mac OS X',
        'iPhone; CPU iPhone OS 15_0 like Mac OS X',
        'Linux; Android 10; SM-G9730',
        'Linux; Android 11; MI 9'
    ]
    
    platform = random.choice(platforms)
    wechat_version = random.choice(wechat_versions)
    
    return f'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/{wechat_version} NetType/WIFI Language/zh_CN'


def get_alipay_user_agent() -> str:
    """生成支付宝内置浏览器User-Agent"""
    alipay_versions = [
        '10.1.90', '10.1.92', '10.1.95', '10.2.0', '10.2.10', '10.2.12',
        '10.2.15', '10.2.20', '10.2.22', '10.2.25', '10.2.28'
    ]
    
    platforms = [
        'iPhone; CPU iPhone OS 14_6 like Mac OS X',
        'Linux; Android 10; SM-G9730',
        'Linux; Android 11; MI 9'
    ]
    
    platform = random.choice(platforms)
    alipay_version = random.choice(alipay_versions)
    
    return f'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{random.randint(70, 90)}.0.3497.100 Mobile Safari/537.36 AlipayDefined() AliApp(AP/{alipay_version})'


def get_douyin_user_agent() -> str:
    """生成抖音内置浏览器User-Agent"""
    douyin_versions = [
        '10.0.0', '10.1.0', '10.2.0', '10.3.0', '10.4.0', '10.5.0',
        '11.0.0', '11.1.0', '11.2.0', '11.3.0', '11.4.0'
    ]
    
    platforms = [
        'iPhone; CPU iPhone OS 14_6 like Mac OS X',
        'Linux; Android 10; SM-G9730',
        'Linux; Android 11; MI 9'
    ]
    
    platform = random.choice(platforms)
    douyin_version = random.choice(douyin_versions)
    
    return f'Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{random.randint(70, 90)}.0.3497.100 Mobile Safari/537.36 aweme_{douyin_version}'


def get_random_user_agent() -> str:
    """随机返回任意类型的User-Agent"""
    ua_types = ['mobile', 'pc', 'wechat', 'alipay', 'douyin']
    ua_type = random.choice(ua_types)
    return get_fake_user_agent(ua_type)


# 兼容旧版本代码
def get_fake_user_agent_old(ua: str, default=True) -> str:
    """旧版本兼容函数"""
    return get_fake_user_agent(ua, default)


if __name__ == "__main__":
    # 测试代码
    print("移动端User-Agent:")
    for i in range(3):
        print(get_fake_user_agent("mobile"))
    
    print("\nPC端User-Agent:")
    for i in range(3):
        print(get_fake_user_agent("pc"))
    
    print("\n微信User-Agent:")
    print(get_fake_user_agent("wechat"))
    
    print("\n随机User-Agent:")
    for i in range(3):
        print(get_random_user_agent())