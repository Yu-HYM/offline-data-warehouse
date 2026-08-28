#!/bin/bash
source /etc/profile 2>/dev/null
source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
P=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$P
LOG=/data/logs/scheduler/2026-08-21/08_ads_export_mysql.log
DT=2026-08-21

# 清理之前 FAILED 状态，防止 run_pipeline 幂等跳过
rm -f /data/scheduler/state/$DT/08_ads_export_mysql.state.latest.json /data/scheduler/state/$DT/08_ads_export_mysql.state.jsonl /data/scheduler/state/$DT/pipeline.state.latest.json

echo "=== 直接跑 export_ads_to_mysql.py ==="
python3 /opt/script/mall/ads/export_ads_to_mysql.py $DT 2>&1 | tee $LOG | tail -40
RC=${PIPESTATUS[0]}
echo "rc=$RC"

echo
echo "=== 验证 mall_ads.ads_trade_stats ==="
mysql -uroot -p123456 mall_ads -N -B -e "SELECT dt,gmv,order_count,pay_user_count,avg_pay_amount FROM ads_trade_stats WHERE dt='$DT';" 2>/dev/null
echo
echo "=== 验证 ads_repurchase_rate ==="
mysql -uroot -p123456 mall_ads -N -B -e "SELECT dt,order_user_count,repurchase_user_count,repurchase_rate FROM ads_repurchase_rate WHERE dt='$DT';" 2>/dev/null
echo
echo "=== 验证 ads_user_rfm 行数 ==="
mysql -uroot -p123456 mall_ads -N -B -e "SELECT dt,COUNT(*) FROM ads_user_rfm WHERE dt='$DT' GROUP BY dt;" 2>/dev/null