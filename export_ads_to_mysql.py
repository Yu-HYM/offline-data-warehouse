#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ADS 导出 Hive -> MySQL mall_ads（阶段七 7.4 + 阶段八 bug 修复）
# 用法: python3 export_ads_to_mysql.py 2026-08-19 2026-08-20
import sys
import os
import subprocess
import pymysql

MYSQL_CONFIG = {'host': 'localhost', 'user': 'root', 'password': '123456', 'database': 'mall_ads', 'charset': 'utf8mb4'}


def hive_query(sql, timeout=300):
    """
    执行 Hive 查询并返回二维数组；空值统一为 None。
    使用临时 SQL 文件 + -f 方式，规避 shell 引号嵌套和中文路径问题。
    """
    ts = str(int(__import__('time').time() * 1000000))
    sql_file = "/tmp/ads_export_" + ts + ".sql"
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(sql + "\n")
    env = os.environ.copy()
    env['JAVA_HOME'] = '/usr/lib/jvm/java-8-openjdk-amd64'
    env['HADOOP_HOME'] = '/opt/module/hadoop-3.3.6'
    env['HIVE_HOME'] = '/opt/module/apache-hive-3.1.3-bin'
    env['PATH'] = (env['JAVA_HOME'] + '/bin:' + env['HADOOP_HOME'] + '/bin:' + env['HIVE_HOME'] +
                   '/bin:' + env['HADOOP_HOME'] + '/sbin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
    cmd = "hive --hiveconf hive.cli.print.header=false -f " + sql_file
    result = subprocess.run(['/bin/bash', '-lc', cmd],
                            capture_output=True, text=True, timeout=timeout, env=env)
    try:
        os.remove(sql_file)
    except Exception:
        pass
    lines = []
    for line in (result.stdout or '').splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if (s.startswith('SLF4J') or s.startswith('Hive') or s.startswith('Logging') or
                s.startswith('Hadoop') or 'time taken' in low or s == 'OK' or
                'fetched' in low or low.startswith('warning:') or 'session id' in low):
            continue
        parts = s.split('\t')
        for i in range(len(parts)):
            if parts[i] == 'NULL' or parts[i] == '':
                parts[i] = None
        lines.append(parts)
    return lines


def create_mysql_tables():
    conn = pymysql.connect(host='localhost', user='root', password='123456', charset='utf8mb4')
    cur = conn.cursor()
    cur.execute('CREATE DATABASE IF NOT EXISTS mall_ads DEFAULT CHARSET utf8mb4')
    cur.execute('USE mall_ads')
    cur.execute("""CREATE TABLE IF NOT EXISTS ads_trade_stats(
        dt VARCHAR(20) PRIMARY KEY, gmv DECIMAL(16,2), order_count BIGINT,
        pay_user_count BIGINT, avg_pay_amount DECIMAL(16,2))
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    cur.execute("""CREATE TABLE IF NOT EXISTS ads_repurchase_rate(
        dt VARCHAR(20) PRIMARY KEY, order_user_count BIGINT,
        repurchase_user_count BIGINT, repurchase_rate DECIMAL(10,4))
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    cur.execute("""CREATE TABLE IF NOT EXISTS ads_user_rfm(
        dt VARCHAR(20), user_id VARCHAR(64), r_score INT, f_score INT,
        m_score INT, rfm_label VARCHAR(32), PRIMARY KEY(dt,user_id))
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    conn.commit()
    cur.close()
    conn.close()
    print('[MySQL] mall_ads 库 + 3 张表就绪')


def batch_insert(table, columns, rows):
    if not rows:
        print('  warn: ' + table + ' 无数据，跳过写入')
        return
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cols = ', '.join(columns)
    ph = ', '.join(['%s'] * len(columns))
    upd = ', '.join(c + '=VALUES(' + c + ')' for c in columns if c not in ('dt', 'user_id'))
    sql = 'INSERT INTO ' + table + ' (' + cols + ') VALUES (' + ph + ')'
    if upd:
        sql += ' ON DUPLICATE KEY UPDATE ' + upd
    cur.executemany(sql, rows)
    conn.commit()
    cur.close()
    conn.close()
    print('  -> ' + table + ': 写入 ' + str(len(rows)) + ' 行')


def _fmt(x):
    return str(x) if x is not None else 'NULL'


def export_trade_stats(dates):
    print('\n[导出] ads_trade_stats')
    rows = []
    for dt in dates:
        r = hive_query(
            "USE mall;\nSELECT '%s', gmv, order_count, pay_user_count, avg_pay_amount "
            "FROM ads_trade_stats WHERE dt='%s';" % (dt, dt))
        if r:
            print('  ' + dt + ': GMV=' + _fmt(r[0][1]) + ' 订单=' + _fmt(r[0][2]) +
                  ' 支付用户=' + _fmt(r[0][3]) + ' 客单价=' + _fmt(r[0][4]))
            rows.extend(tuple(x) for x in r)
        else:
            print('  warn: ' + dt + ' 在 Hive ads_trade_stats 中无数据，跳过')
    batch_insert('ads_trade_stats', ['dt', 'gmv', 'order_count', 'pay_user_count', 'avg_pay_amount'], rows)


def export_repurchase_rate(dates):
    print('\n[导出] ads_repurchase_rate')
    rows = []
    for dt in dates:
        r = hive_query(
            "USE mall;\nSELECT '%s', order_user_count, repurchase_user_count, repurchase_rate "
            "FROM ads_repurchase_rate WHERE dt='%s';" % (dt, dt))
        if r:
            print('  ' + dt + ': 下单用户=' + _fmt(r[0][1]) + ' 复购用户=' + _fmt(r[0][2]) +
                  ' 复购率=' + _fmt(r[0][3]))
            rows.extend(tuple(x) for x in r)
        else:
            print('  warn: ' + dt + ' 在 Hive ads_repurchase_rate 中无数据，跳过')
    batch_insert('ads_repurchase_rate', ['dt', 'order_user_count', 'repurchase_user_count', 'repurchase_rate'], rows)


def export_user_rfm(dates):
    print('\n[导出] ads_user_rfm')
    rows = []
    for dt in dates:
        r = hive_query(
            "USE mall;\nSELECT '%s', user_id, r_score, f_score, m_score, rfm_label "
            "FROM ads_user_rfm WHERE dt='%s';" % (dt, dt))
        print('  ' + dt + ': ' + str(len(r)) + ' 行')
        rows.extend(tuple(x) for x in r)
    batch_insert('ads_user_rfm', ['dt', 'user_id', 'r_score', 'f_score', 'm_score', 'rfm_label'], rows)


def main():
    dates = sys.argv[1:] if len(sys.argv) > 1 else ['2026-08-19', '2026-08-20']
    print('=' * 60)
    print('# ADS 导出 Hive -> MySQL mall_ads')
    print('# 日期: ' + ', '.join(dates))
    print('=' * 60)
    create_mysql_tables()
    export_trade_stats(dates)
    export_repurchase_rate(dates)
    export_user_rfm(dates)
    print('\n' + '=' * 60)
    print('# 导出完成，可接入 BI 报表')
    print('=' * 60)


if __name__ == '__main__':
    main()