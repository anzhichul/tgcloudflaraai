import pymysql
import time
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PWD, MYSQL_DB

# 建立MySQL数据库连接（增加超时、重试、防卡死配置）
def get_db_conn(retry=2):
    for i in range(retry):
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PWD,
                database=MYSQL_DB,
                charset="utf8mb4",
                connect_timeout=10,  # 连接超时10秒
                read_timeout=15,     # 读超时15秒
                write_timeout=15,    # 写超时15秒
                autocommit=True,     # 自动提交，避免事务阻塞
                cursorclass=pymysql.cursors.DictCursor
            )
            return conn
        except Exception as e:
            if i == retry - 1:  # 最后一次重试失败，抛出异常
                raise e
            time.sleep(1)       # 重试间隔1秒
    raise Exception("MySQL连接重试失败")

# 初始化数据库（创建表，首次运行执行）
def init_db():
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.close()
        conn.close()
        print("MySQL数据库初始化成功 ✅")
    except Exception as e:
        print(f"MySQL初始化失败: {e}")
        raise e

# 执行增/删/改SQL操作
def execute(sql, args=()):
    conn = None
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(sql, args)
        return True
    except Exception as e:
        print(f"SQL执行失败: {sql} | {args} | {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# 执行查询SQL操作，转换为原SQLite兼容的元组格式
def query(sql, args=()):
    conn = None
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(sql, args)
        res = cursor.fetchall()
        # 转换为元组列表，兼容原有代码
        return [tuple(item.values()) for item in res] if res else []
    except Exception as e:
        print(f"SQL查询失败: {sql} | {args} | {e}")
        return []
    finally:
        if conn:
            conn.close()
