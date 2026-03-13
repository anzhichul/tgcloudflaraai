import requests
from db import execute, query

# Cloudflare AI 版本，接口替换，结构和原来完全一致
def ai_reply(text):
    try:
        account_id = ""
        api_token = ""
        
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        data = {
            "messages": [
                {"role": "user", "content": text}
            ]
        }

        resp = requests.post(url, json=data, headers=headers, timeout=15)
        j = resp.json()

        if "result" in j and "response" in j["result"]:
            return j["result"]["response"]
        else:
            return "⚠️ AI 密钥错误或额度已用完，请联系管理员"
    except Exception as e:
        return "⚠️ AI 服务异常"
