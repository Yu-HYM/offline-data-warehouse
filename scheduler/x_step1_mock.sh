#!/usr/bin/env bash
source /etc/profile 2>/dev/null; source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$PATH"

DT=2026-08-21
echo "=== 1. mock day $DT ==="
python3 /opt/script/mall/mock/mock_data.py day "$DT" 2>&1 | tail -10
echo
echo "=== 2. ??? ==="
Q="SELECT COUNT(*) FROM order_info WHERE DATE(create_time)='%s'"
mysql -uroot -p123456 mall -N -B -e "$(printf "$Q" "$DT")" 2>/tmp/m.log || cat /tmp/m.log
echo "=== 3. ??? ==="
Q2="SELECT COUNT(*) FROM action_log WHERE DATE(create_time)='%s'"
mysql -uroot -p123456 mall -N -B -e "$(printf "$Q2" "$DT")" 2>/dev/null
echo "=== 4. Hive mall ???? ORC ADS ? ==="
hive -e "USE mall; SHOW TABLES LIKE 'ads%';" 2>/dev/null | head -10
