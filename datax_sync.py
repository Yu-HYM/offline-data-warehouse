import pymysql
import csv
import os
from datetime import datetime

MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'mall',
    'charset': 'utf8mb4'
}

OUTPUT_DIR = '/home/hadoop/mall_ods'

def extract_mysql():
    """从 MySQL 抽取数据"""
    print(f"[{datetime.now()}] 开始从 {MYSQL_CONFIG['database']} 抽取数据...")

    tables = ['user_info', 'product_info', 'order_info']
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  表 {table}: {count} 行")

            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()

            if rows:
                filepath = f"{OUTPUT_DIR}/{table}.csv"
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=',')
                    for row in rows:
                        writer.writerow([str(v) if v is not None else '' for v in row])
                print(f"    已写入: {filepath}")
        except Exception as e:
            print(f"    跳过 {table}: {e}")

    cursor.close()
    conn.close()
    print(f"[{datetime.now()}] 数据抽取完成")

if __name__ == '__main__':
    extract_mysql()
