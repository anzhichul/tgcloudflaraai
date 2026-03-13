import requests
import json
import time
import random
from collections import defaultdict
from config import *
from db import init_db, execute, query
from user import *

# 初始化数据库
init_db()
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
admin_action = {}
user_memory = defaultdict(list)
# 频道信息
CHANNEL_CHAT_ID = -1003663591656
CHANNEL_LINK = "https://t.me/mtproxysv"
# Telegram单条消息最大支持4096字符，设4000留缓冲区
MAX_MSG_LEN = 4000

# 日志记录函数（异常全捕获，避免变量未定义）
def log(uid, text):
    try:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        log_str = f"[{now}] UID:{uid} | {text}"
        print(log_str)
        with open("bot.log", "a", encoding="utf-8") as f:
            f.write(log_str + "\n")
    except Exception as e:
        print(f"日志操作失败: {e}")


# 发送Telegram消息函数（修复版：纯文本、不解析、必达）
def send(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "",
        "disable_web_page_preview": True
    }
    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        res = requests.post(url, json=data, timeout=15)
    except Exception as e:
        log(0, f"发送消息失败: {e}")

# 消息分段函数
def split_msg(text):
    chunks = []
    start = 0
    while start < len(text):
        end = start + MAX_MSG_LEN
        if end < len(text):
            split_pos = text.rfind('\n', start, end)
            if split_pos == -1:
                split_pos = end
            chunks.append(text[start:split_pos])
            start = split_pos
        else:
            chunks.append(text[start:])
            break
    return chunks

# 普通用户主菜单
def main_menu(user_id=None):
    return {
        "keyboard": [
            [{"text":"💬 开始聊天"}, {"text":"🧹 清空记忆"}],
            [{"text":"📌 帮助"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# 频道验证内联菜单
def channel_menu():
    return {
        "inline_keyboard": [
            [{"text":"✅ 加入频道", "url": CHANNEL_LINK}],
            [{"text":"🔄 已加入，重新验证", "callback_data":"check_channel"}]
        ]
    }

# 检测用户是否加入指定频道
def is_user_in_channel(user_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
        payload = {
            "chat_id": CHANNEL_CHAT_ID,
            "user_id": user_id
        }
        r = requests.get(url, params=payload, timeout=10)
        data = r.json()
        if not data.get("ok"):
            return False
        status = data["result"]["status"]
        allowed = ["creator", "administrator", "member"]
        return status in allowed
    except:
        return False

# 检测消息是否包含违禁词
def check_bad(text):
    words = get_forbidden()
    for w in words:
        if w in text:
            return True
    return False

# ======================
# 关键词规则（网页后台管理）
# ======================
def get_rules():
    try:
        rows = query("SELECT keyword, reply FROM rules ORDER BY id DESC")
        rules = [{"keyword": row[0], "reply": row[1]} for row in rows]
        return rules
    except Exception as e:
        log(0, f"读取规则失败: {e}")
        return []

def rule_match(text):
    rules = get_rules()
    for rule in rules:
        if rule["keyword"] in text:
            return rule["reply"]
    return None

# ======================
# 全局 AI 规则（从数据库读取，实时生效）
# ======================
def get_global_system_prompt():
    try:
        row = query("SELECT rule_text FROM global_rules ORDER BY id DESC LIMIT 1")
        if row:
            return row[0][0]
        else:
            return "你是一个友好、有礼貌的AI助手。不讨论敏感政治、违法、暴力、色情内容，遇到此类问题请温和拒绝。"
    except:
        return "你是一个友好、有礼貌的AI助手。不讨论敏感政治、违法、暴力、色情内容，遇到此类问题请温和拒绝。"

# ======================
# AI 回复（Cloudflare Llama 3.1 8B 免费）
# ======================
def ai_reply(text, user_id):
    # 1. 优先关键词规则
    rule_reply = rule_match(text)
    if rule_reply is not None:
        return rule_reply

    # 2. 违禁词拦截
    if check_bad(text):
        return "⚠️ 内容不合适，我无法回答。"

    try:
        # Cloudflare API配置
        account_id = ""  # Cloudflare账户ID
        api_token = ""  # Cloudflare API令牌

        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        # 全局规则（每次对话都重新读取，自动更新）
        system_prompt = get_global_system_prompt()

        # 构造上下文
        messages = [{"role": "system", "content": system_prompt}]
        messages += user_memory[user_id].copy()
        messages.append({"role": "user", "content": text})

        data = {"messages": messages}
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        j = resp.json()

        if "result" in j and "response" in j["result"]:
            reply = j["result"]["response"].strip()

            user_memory[user_id].append({"role": "user", "content": text})
            user_memory[user_id].append({"role": "assistant", "content": reply})

            # 限制记忆长度
            if len(user_memory[user_id]) > 20:
                user_memory[user_id] = user_memory[user_id][-20:]
            return reply
        else:
            return "我听着呢，你可以换个问题～"
    except Exception as e:
        log(user_id, f"AI错误: {e}")
        return "服务繁忙，请稍后再试。"

# 聊天记录
def add_chat_history(user_id, role, content):
    execute(
        "INSERT INTO messages (user_id, role, content, time) VALUES (%s, %s, %s, %s)",
        (user_id, role, content, time.strftime('%Y-%m-%d %H:%M:%S'))
    )

# ======================
# 消息处理
# ======================
def handle_message(msg):
    if "chat" not in msg or "from" not in msg:
        return
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    first_name = msg["from"].get("first_name", "")
    username = msg["from"].get("username", "")
    text = msg.get("text", "").strip()

    init_user(user_id, username, first_name)
    log(user_id, text)

    # 封禁检查
    if is_banned(user_id):
        send(chat_id, "❌ 你已被拉黑封禁\n请联系 @minixpc")
        return

    # 频道检查
    if not is_user_in_channel(user_id):
        send(chat_id, "🔔 请先加入频道，才能使用机器人功能", channel_menu())
        return

    # /start
    if text == "/start":
        welcome = f"""
👋 你好 {first_name}
✅ 您已加入频道，感谢使用
本机器人由安安创建
联系方式：@minixpc
"""
        send(chat_id, welcome.strip(), main_menu(user_id))
        return

    # 清空记忆
    if text == "🧹 清空记忆":
        user_memory[user_id] = []
        send(chat_id, "✅ 已清空你的对话记忆")
        return

    # 帮助
    if text == "📌 帮助":
        help_text = """
📌 功能说明
• 直接发消息 = AI 智能对话
• 🧹 清空记忆 = 重置上下文
"""
        send(chat_id, help_text.strip())
        return

    # 正常 AI 对话
    ans = ai_reply(text, user_id)
    add_chat_history(user_id, "user", text)
    add_chat_history(user_id, "assistant", ans)

    if len(ans) <= MAX_MSG_LEN:
        send(chat_id, ans)
    else:
        for chunk in split_msg(ans):
            send(chat_id, chunk)
            time.sleep(0.3)

# 处理频道验证
def handle_callback(call):
    user_id = call["from"]["id"]
    chat_id = call["message"]["chat"]["id"]
    if is_user_in_channel(user_id):
        send(chat_id, "✅ 验证成功！可以聊天啦", main_menu(user_id))
    else:
        send(chat_id, "❌ 请先加入频道", channel_menu())

# 主循环
def run():
    log(0, "机器人启动成功 ✅")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            payload = {
                "offset": offset,
                "timeout": 20,
                "allowed_updates": ["message", "callback_query"]
            }
            resp = requests.get(url, params=payload, timeout=25)
            data = resp.json()
            if data.get("ok") and data.get("result"):
                for item in data["result"]:
                    offset = item["update_id"] + 1
                    if "message" in item:
                        handle_message(item["message"])
                    elif "callback_query" in item:
                        handle_callback(item["callback_query"])
        except Exception as e:
            log(0, f"循环异常: {e}")
            time.sleep(2)

if __name__ == "__main__":
    run()