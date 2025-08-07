#!/usr/bin/env python3
"""
简单的 token 获取工具
"""

import requests
import json
from urllib.parse import urlencode

def get_manual_token():
    """
    手动获取 token 的简化方法
    """
    tenant_id = "4abc24ea-2d0b-4011-87d4-3de32ca1e9cc"
    client_id = "51f81489-12ee-4a9e-aaae-a2591f45987d"
    resource_url = "https://aurorabapenv87b96.crm10.dynamics.com/"
    redirect_url = "https://localhost"
    
    # 生成授权 URL
    auth_endpoint = "https://login.microsoftonline.com/common/oauth2/authorize"
    auth_params = {
        'resource': resource_url,
        'client_id': client_id,
        'redirect_uri': redirect_url,
        'response_type': 'token',
        'prompt': 'login'
    }
    
    auth_url = f"{auth_endpoint}?{urlencode(auth_params)}"
    
    print("=" * 80)
    print("🔑 手动获取 ACCESS TOKEN")
    print("=" * 80)
    print("请按照以下步骤操作：")
    print()
    print("1. 复制下面的 URL 并在浏览器中打开：")
    print(f"   {auth_url}")
    print()
    print("2. 使用你的 Azure 凭据登录")
    print()
    print("3. 登录成功后，你会被重定向到 localhost")
    print("   URL 会类似这样: https://localhost/#access_token=eyJ0eXAi...")
    print()
    print("4. 从 URL 中复制 access_token 的值（从 access_token= 到 &token_type 之间的部分）")
    print()
    print("5. 将 token 粘贴到 token.config 文件中")
    print()
    print("6. 重新运行你的脚本")
    print()
    print("=" * 80)
    print("💡 提示：token 有效期约为 1 小时")
    print("💡 建议：对于大批量处理，考虑设置 refresh_token 自动刷新")
    print("=" * 80)

def check_current_token():
    """检查当前 token 状态"""
    try:
        import base64
        from datetime import datetime, timezone
        
        print("\n🔍 检查当前 token 状态...")
        
        with open('token.config', 'r') as f:
            token = f.read().strip()
        
        # 解码 JWT payload
        parts = token.split('.')
        payload = parts[1]
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
        
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_json = json.loads(decoded_bytes.decode('utf-8'))
        
        # 检查过期时间
        exp_timestamp = decoded_json.get('exp')
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        current_time = datetime.now(tz=timezone.utc)
        
        print(f"📅 Token 过期时间: {exp_datetime}")
        print(f"⏰ 当前时间: {current_time}")
        
        if current_time >= exp_datetime:
            print("❌ Token 已过期")
            return False
        else:
            remaining = exp_datetime - current_time
            print(f"✅ Token 仍有效，剩余时间: {remaining}")
            return True
            
    except Exception as e:
        print(f"❌ 检查 token 时出错: {e}")
        return False

if __name__ == "__main__":
    # 首先检查当前 token
    if check_current_token():
        print("\n✅ 当前 token 仍然有效，无需刷新")
    else:
        print("\n❌ 需要获取新的 token")
        get_manual_token()
