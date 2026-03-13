# 运行一次就检查所有用户是否还在频道
# 不在 → 删除用户
import time
from start import bot
from user import get_all_users, delete_user, check_user_in_channel
from config import REQUIRED_CHANNEL

def run_daily_check():
    print("🔍 开始全量检测频道成员…")
    users = get_all_users()
    for (uid,) in users:
        try:
            if not check_user_in_channel(uid):
                delete_user(uid)
                print(f"🗑 已删除退出频道用户: {uid}")
            time.sleep(0.5)
        except:
            continue
    print("✅ 检测完成")

if __name__ == "__main__":
    run_daily_check()
