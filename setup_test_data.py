import pymysql

conn = pymysql.connect(host='localhost', port=3306, user='root', password='123456', database='mall', charset='utf8mb4')
cursor = conn.cursor()

tables_sql = """
CREATE TABLE IF NOT EXISTS user_info (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(50),
    age INT,
    gender VARCHAR(10),
    city VARCHAR(50),
    create_time DATETIME
);

CREATE TABLE IF NOT EXISTS product_info (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10,2),
    stock INT,
    create_time DATETIME
);

CREATE TABLE IF NOT EXISTS order_info (
    order_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    product_id BIGINT,
    quantity INT,
    amount DECIMAL(10,2),
    order_status VARCHAR(20),
    create_time DATETIME
);
"""

for sql in tables_sql.strip().split(';'):
    if sql.strip():
        cursor.execute(sql)
        print(f"执行: {sql[:60]}...")

cursor.execute("SELECT COUNT(*) FROM user_info")
if cursor.fetchone()[0] == 0:
    users = [
        (1, '张三', 28, '男', '北京', '2024-01-15 10:30:00'),
        (2, '李四', 35, '女', '上海', '2024-02-20 14:00:00'),
        (3, '王五', 22, '男', '广州', '2024-03-10 09:15:00'),
        (4, '赵六', 41, '女', '深圳', '2024-04-05 16:45:00'),
        (5, '钱七', 30, '男', '杭州', '2024-05-22 11:20:00'),
        (6, '孙八', 27, '女', '成都', '2024-06-18 13:00:00'),
        (7, '周九', 33, '男', '武汉', '2024-07-01 15:30:00'),
        (8, '吴十', 26, '女', '南京', '2024-08-14 08:45:00'),
    ]
    cursor.executemany("INSERT INTO user_info VALUES (%s,%s,%s,%s,%s,%s)", users)
    print(f"插入 {len(users)} 条用户数据")

cursor.execute("SELECT COUNT(*) FROM product_info")
if cursor.fetchone()[0] == 0:
    products = [
        (101, 'iPhone 15', '手机数码', 5999.00, 1000, '2024-01-01 00:00:00'),
        (102, '华为Mate60', '手机数码', 6999.00, 800, '2024-01-01 00:00:00'),
        (103, '小米14', '手机数码', 3999.00, 1500, '2024-02-01 00:00:00'),
        (104, 'MacBook Pro', '电脑办公', 15999.00, 500, '2024-03-01 00:00:00'),
        (105, 'ThinkPad X1', '电脑办公', 12999.00, 300, '2024-03-15 00:00:00'),
        (106, 'AirPods Pro', '影音娱乐', 1899.00, 2000, '2024-04-01 00:00:00'),
        (107, 'Kindle', '图书文娱', 999.00, 1000, '2024-05-01 00:00:00'),
        (108, '戴森吸尘器', '家用电器', 4599.00, 600, '2024-06-01 00:00:00'),
    ]
    cursor.executemany("INSERT INTO product_info VALUES (%s,%s,%s,%s,%s,%s)", products)
    print(f"插入 {len(products)} 条商品数据")

cursor.execute("SELECT COUNT(*) FROM order_info")
if cursor.fetchone()[0] == 0:
    orders = [
        (1001, 1, 101, 1, 5999.00, '已完成', '2024-08-01 10:00:00'),
        (1002, 2, 104, 1, 15999.00, '已完成', '2024-08-02 11:30:00'),
        (1003, 3, 106, 2, 3798.00, '已完成', '2024-08-05 14:00:00'),
        (1004, 1, 102, 1, 6999.00, '已发货', '2024-08-10 09:00:00'),
        (1005, 4, 108, 1, 4599.00, '已完成', '2024-08-12 16:00:00'),
        (1006, 5, 103, 3, 11997.00, '待付款', '2024-08-15 12:00:00'),
        (1007, 6, 105, 1, 12999.00, '已完成', '2024-08-18 15:30:00'),
        (1008, 7, 107, 2, 1998.00, '已发货', '2024-08-20 10:00:00'),
        (1009, 8, 101, 1, 5999.00, '已完成', '2024-08-22 14:45:00'),
        (1010, 2, 106, 1, 1899.00, '已完成', '2024-08-25 09:30:00'),
    ]
    cursor.executemany("INSERT INTO order_info VALUES (%s,%s,%s,%s,%s,%s,%s)", orders)
    print(f"插入 {len(orders)} 条订单数据")

conn.commit()
cursor.close()
conn.close()
print("测试数据准备完成")
