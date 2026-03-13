from db import execute, query
import time

# 初始化用户信息（首次使用机器人时创建）
def init_user(user_id, username, first_name):
    r = query("SELECT 1 FROM users WHERE user_id=%s", (user_id,))
    if not r:
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        execute(
            "INSERT INTO users (user_id, username, first_name, created_at) VALUES (%s,%s,%s,%s)",
            (user_id, username, first_name, t)
        )

# 判断用户是否被封禁
def is_banned(user_id):
    r = query("SELECT banned FROM users WHERE user_id=%s", (user_id,))
    return r and r[0][0] == 1

# 封禁用户 + 写入封禁日志
def ban(user_id, admin_id, reason='无'):
    execute("UPDATE users SET banned=1 WHERE user_id=%s", (user_id,))
    ban_time = time.strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "INSERT INTO ban_log (banned_user_id, admin_id, ban_time, ban_reason) VALUES (%s,%s,%s,%s)",
        (user_id, admin_id, ban_time, reason)
    )

# 解封用户 + 更新封禁日志
def unban(user_id, admin_id):
    execute("UPDATE users SET banned=0 WHERE user_id=%s", (user_id,))
    unban_time = time.strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "UPDATE ban_log SET is_unban=1, unban_time=%s WHERE banned_user_id=%s AND is_unban=0",
        (unban_time, user_id)
    )

# 增加用户聊天次数
def add_chat_count(user_id):
    execute("UPDATE users SET chat_count=chat_count+1 WHERE user_id=%s", (user_id,))

# 获取用户基础信息
def get_user_info(user_id):
    r = query("SELECT username,chat_count,banned FROM users WHERE user_id=%s", (user_id,))
    return r[0] if r else []

# 获取用户聊天记录
def get_chat_history(user_id):
    return query("SELECT role,content,time FROM messages WHERE user_id=%s ORDER BY id", (user_id,))

# 添加违禁词
def add_forbidden(word):
    execute("INSERT IGNORE INTO forbidden (word) VALUES (%s)", (word,))

# 删除违禁词
def del_forbidden(word):
    execute("DELETE FROM forbidden WHERE word=%s", (word,))

# 获取所有违禁词
def get_forbidden():
    r = query("SELECT word FROM forbidden")
    return [i[0] for i in r] if r else []

# 查询用户封禁日志
def get_ban_log(user_id):
    return query("SELECT * FROM ban_log WHERE banned_user_id=%s ORDER BY id DESC", (user_id,))
