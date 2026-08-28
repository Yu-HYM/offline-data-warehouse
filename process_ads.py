#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADS 指标层加工脚本（阶段七）

从 DWS ORC 内部表（dws_trade_user_order_1d）读取数据，
计算三组核心指标后写入 ADS ORC 内部表：
  1. ads_trade_stats     每日交易核心指标（GMV/订单数/支付用户数/客单价）
  2. ads_repurchase_rate 复购率（当日下单用户中累计下单>=2次的占比）
  3. ads_user_rfm        近30天 RFM 用户分层（R/F/M 三维5档打分 + 8类标签）

用法:
  python3 process_ads.py 2026-08-19
  python3 process_ads.py 2026-08-19 2026-08-20
"""

import sys
import os
import subprocess


def run_hive_sql(hive_sql, tag, timeout=300):
    """执行 Hive SQL 文件"""
    sql_file = f"/tmp/process_ads_{tag}.sql"
    with open(sql_file, 'w') as f:
        f.write(hive_sql)

    cmd = f"source ~/.profile && hive -f {sql_file} 2>&1 | grep -E 'OK|FAILED|Time taken|Error|指标|用户数|复购|RFM' | tail -15"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, executable='/bin/bash'
        )
        print(f"  {result.stdout.strip()}")
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Hive 执行超时 ({timeout}s)")
        return -1
    finally:
        if os.path.exists(sql_file):
            os.remove(sql_file)


# ==================== 1. 每日交易核心指标 ====================

def process_ads_trade_stats(dt):
    """ads_trade_stats：GMV、订单数、支付用户数、客单价"""
    print(f"\n[ADS] 每日交易核心指标 (ads_trade_stats) dt={dt}")

    hive_sql = f"""
USE mall;

SET hive.exec.mode.local.auto=true;
SET hive.exec.mode.local.auto.inputbytes.max=128000000;

INSERT OVERWRITE TABLE ads_trade_stats PARTITION (dt='{dt}')
SELECT
    SUM(order_amount_1d)                                          AS gmv,
    SUM(order_count_1d)                                           AS order_count,
    COUNT(DISTINCT CASE WHEN pay_amount_1d > 0 THEN user_id END) AS pay_user_count,
    ROUND(SUM(order_amount_1d) / SUM(order_count_1d), 2)          AS avg_pay_amount
FROM dws_trade_user_order_1d
WHERE dt = '{dt}';

SELECT '指标:GMV' AS info, gmv FROM ads_trade_stats WHERE dt='{dt}';
SELECT '指标:订单数' AS info, order_count FROM ads_trade_stats WHERE dt='{dt}';
SELECT '指标:支付用户数' AS info, pay_user_count FROM ads_trade_stats WHERE dt='{dt}';
SELECT '指标:客单价' AS info, avg_pay_amount FROM ads_trade_stats WHERE dt='{dt}';
"""
    run_hive_sql(hive_sql, f'trade_{dt}')


# ==================== 2. 复购率 ====================

def process_ads_repurchase_rate(dt):
    """ads_repurchase_rate：当日下单用户中累计下单>=2次的占比"""
    print(f"\n[ADS] 复购率指标 (ads_repurchase_rate) dt={dt}")

    hive_sql = f"""
USE mall;

SET hive.exec.mode.local.auto=true;
SET hive.exec.mode.local.auto.inputbytes.max=128000000;

INSERT OVERWRITE TABLE ads_repurchase_rate PARTITION (dt='{dt}')
SELECT
    COUNT(DISTINCT t1.user_id)                                AS order_user_count,
    COUNT(DISTINCT CASE WHEN t2.cnt >= 2 THEN t1.user_id END) AS repurchase_user_count,
    ROUND(
        COUNT(DISTINCT CASE WHEN t2.cnt >= 2 THEN t1.user_id END) /
        COUNT(DISTINCT t1.user_id), 4
    )                                                          AS repurchase_rate
FROM (
    SELECT DISTINCT user_id
    FROM dws_trade_user_order_1d
    WHERE dt = '{dt}'
) t1
JOIN (
    SELECT user_id, COUNT(*) AS cnt
    FROM dws_trade_user_order_1d
    WHERE dt <= '{dt}'
    GROUP BY user_id
) t2
ON t1.user_id = t2.user_id;

SELECT '当日下单用户数' AS info, order_user_count FROM ads_repurchase_rate WHERE dt='{dt}';
SELECT '复购用户数' AS info, repurchase_user_count FROM ads_repurchase_rate WHERE dt='{dt}';
SELECT '复购率' AS info, repurchase_rate FROM ads_repurchase_rate WHERE dt='{dt}';
"""
    run_hive_sql(hive_sql, f'repurchase_{dt}')


# ==================== 3. RFM 用户分层 ====================

def process_ads_user_rfm(dt):
    """ads_user_rfm：近30天窗口 R/F/M 三维5档打分 + 8类标签"""
    print(f"\n[ADS] RFM 用户分层 (ads_user_rfm) dt={dt}")

    hive_sql = f"""
USE mall;

SET hive.exec.mode.local.auto=true;
SET hive.exec.mode.local.auto.inputbytes.max=128000000;

INSERT OVERWRITE TABLE ads_user_rfm PARTITION (dt='{dt}')
SELECT
    user_id,
    r_score,
    f_score,
    m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN '重要价值用户'
        WHEN r_score <  3 AND f_score >= 3 AND m_score >= 3 THEN '重要保持用户'
        WHEN r_score >= 3 AND f_score <  3 AND m_score >= 3 THEN '重要发展用户'
        WHEN r_score <  3 AND f_score <  3 AND m_score >= 3 THEN '重要挽留用户'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score <  3 THEN '一般价值用户'
        WHEN r_score <  3 AND f_score >= 3 AND m_score <  3 THEN '一般保持用户'
        WHEN r_score >= 3 AND f_score <  3 AND m_score <  3 THEN '一般发展用户'
        WHEN r_score <  3 AND f_score <  3 AND m_score <  3 THEN '一般挽留用户'
        ELSE '未分层用户'
    END AS rfm_label
FROM (
    SELECT
        user_id,
        -- R 分数：最近消费距今天数越小越好（天数小→tile=1→反转得5分）
        (6 - NTILE(5) OVER (ORDER BY r_days ASC))  AS r_score,
        -- F 分数：消费频次越大越好
        NTILE(5) OVER (ORDER BY f_count ASC)        AS f_score,
        -- M 分数：消费金额越大越好
        NTILE(5) OVER (ORDER BY m_amount ASC)       AS m_score
    FROM (
        SELECT
            user_id,
            DATEDIFF('{dt}', MAX(dt)) AS r_days,
            COUNT(*)                  AS f_count,
            SUM(order_amount_1d)      AS m_amount
        FROM dws_trade_user_order_1d
        WHERE dt BETWEEN DATE_SUB('{dt}', 29) AND '{dt}'
        GROUP BY user_id
    ) rfm
) scored;

SELECT 'RFM用户数' AS info, COUNT(*) AS cnt FROM ads_user_rfm WHERE dt='{dt}';
SELECT rfm_label, COUNT(*) AS cnt
FROM ads_user_rfm
WHERE dt='{dt}'
GROUP BY rfm_label
ORDER BY cnt DESC;
"""
    run_hive_sql(hive_sql, f'rfm_{dt}', timeout=420)


# ==================== 主入口 ====================

def main():
    if len(sys.argv) < 2:
        print("用法: python3 process_ads.py <日期1> [日期2] ...")
        sys.exit(1)

    dates = sys.argv[1:]

    print("=" * 60)
    print("# ADS 指标层加工（从 DWS → ADS）")
    print(f"# 日期: {', '.join(dates)}")
    print("=" * 60)

    for dt in dates:
        process_ads_trade_stats(dt)
        process_ads_repurchase_rate(dt)
        process_ads_user_rfm(dt)

    print("\n" + "=" * 60)
    print("# ADS 加工完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
