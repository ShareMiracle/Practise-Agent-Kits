"""
测试 Twitter API 凭据是否有效
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_credentials():
    """检查 Twitter 凭据配置"""
    print("\n" + "="*60)
    print("Twitter API 凭据检查")
    print("="*60 + "\n")
    
    credentials = {
        "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY", ""),
        "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET", ""),
        "TWITTER_ACCESS_TOKEN": os.getenv("TWITTER_ACCESS_TOKEN", ""),
        "TWITTER_ACCESS_SECRET": os.getenv("TWITTER_ACCESS_SECRET", ""),
        "TWITTER_BEARER_TOKEN": os.getenv("TWITTER_BEARER_TOKEN", ""),
    }
    
    missing = []
    placeholder = []
    
    for key, value in credentials.items():
        if not value:
            missing.append(key)
            print(f"❌ {key}: 未配置")
        elif value.startswith("your_"):
            placeholder.append(key)
            print(f"⚠️  {key}: 占位符（需要替换）")
        else:
            # 只显示前后几个字符
            masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "****"
            print(f"✅ {key}: {masked}")
    
    print("\n" + "="*60)
    
    if missing:
        print(f"\n❌ 缺失 {len(missing)} 个凭据:")
        for key in missing:
            print(f"   - {key}")
    
    if placeholder:
        print(f"\n⚠️  {len(placeholder)} 个凭据需要替换为真实值:")
        for key in placeholder:
            print(f"   - {key}")
    
    if not missing and not placeholder:
        print("\n✅ 所有凭据已配置，准备测试连接...")
        return True
    else:
        print("\n❌ 请先在 .env 文件中配置完整的 Twitter API 凭据")
        print("\n获取凭据的步骤:")
        print("1. 访问 https://developer.twitter.com/en/portal/dashboard")
        print("2. 创建或选择一个 App")
        print("3. 在 'Keys and tokens' 页面生成:")
        print("   - API Key and Secret")
        print("   - Access Token and Secret")
        print("   - Bearer Token (可选，用于只读操作)")
        return False

def test_connection():
    """测试 Twitter API 连接"""
    try:
        import tweepy
        
        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        
        print("\n" + "="*60)
        print("测试 Twitter API 连接")
        print("="*60 + "\n")
        
        # 创建客户端
        client = tweepy.Client(
            bearer_token=bearer_token if bearer_token and not bearer_token.startswith("your_") else None,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )
        
        # 尝试获取用户信息
        print("正在验证凭据...")
        me = client.get_me()
        
        if me.data:
            print(f"\n✅ 连接成功！")
            print(f"   用户名: @{me.data.username}")
            print(f"   用户ID: {me.data.id}")
            print(f"   昵称: {me.data.name}")
            return True
        else:
            print("\n❌ 无法获取用户信息")
            return False
            
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print(f"\n错误详情: {type(e).__name__}")
        
        if "401" in str(e):
            print("\n可能的原因:")
            print("- API 凭据不正确")
            print("- Access Token 和 Secret 不匹配")
            print("- App 权限不足（需要 Read and Write 权限）")
        elif "403" in str(e):
            print("\n可能的原因:")
            print("- App 权限不足")
            print("- 账号被限制")
        
        return False

if __name__ == "__main__":
    # 检查凭据配置
    if check_credentials():
        # 测试连接
        if test_connection():
            print("\n" + "="*60)
            print("✅ 准备就绪，可以运行新闻发布测试")
            print("="*60 + "\n")
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.exit(1)
