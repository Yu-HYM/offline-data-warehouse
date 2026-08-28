#!/usr/bin/env bash
source /etc/profile 2>/dev/null
source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
ORIG_PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$ORIG_PATH

cp "/mnt/e/????/01-??????/create_ads_tables.sql" /tmp/create_ads_tables.sql
ls -la /tmp/create_ads_tables.sql
echo "--- run hive ---"
hive -f /tmp/create_ads_tables.sql 2>&1 | tail -30
echo "--- verify ads tables ---"
hive -S -e 'USE mall; SHOW TABLES LIKE "ads%";' 2>&1
