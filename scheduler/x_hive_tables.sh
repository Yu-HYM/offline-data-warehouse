#!/usr/bin/env bash
source /etc/profile 2>/dev/null; source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$PATH
SQL='USE mall; SHOW TABLES;'
hive -S -e "$SQL" 2>&1 | grep -E "dws|ads"
