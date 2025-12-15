import pymysql

# 替换为你的配置
config = {
    'host': '172.16.121.112',
    'port': 3306,
    'user': 'remote_weibo',
    'password': '123456',
    'database': 'ceshishuju',
    'charset': 'utf8mb4'
}

try:
    conn = pymysql.connect(**config)
    print("MySQL连接成功！")
    conn.close()
except pymysql.OperationalError as e:
    print(f"连接失败：{e}")

with pymysql.connect(**config) as conn, conn.cursor(pymysql.cursors.DictCursor) as cur:
    cur.execute("SELECT * FROM article;")
    for data in cur.fetchall():
        print(data)
