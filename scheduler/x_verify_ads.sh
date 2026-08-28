#!/bin/bash
source /etc/profile; source ~/.profile
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
P=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$P
DT=2026-08-21
echo "--- ads_trade_stats partition ---"
hive -S -e "USE mall; SELECT gmv,order_count,pay_user_count,avg_pay_amount FROM ads_trade_stats WHERE dt='$DT';" 2>/dev/null
echo "--- dws_trade_user_order_1d rows ---"
hive -S -e "USE mall; SELECT COUNT(*), SUM(order_count_1d), SUM(order_amount_1d) FROM dws_trade_user_order_1d WHERE dt='$DT';" 2>/dev/null
echo "--- ads_repurchase_rate rows ---"
hive -S -e "USE mall; SELECT * FROM ads_repurchase_rate WHERE dt='$DT';" 2>/dev/null
echo "--- ads_user_rfm count ---"
hive -S -e "USE mall; SELECT COUNT(*) FROM ads_user_rfm WHERE dt='$DT';" 2>/dev/null