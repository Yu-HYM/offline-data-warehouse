#!/bin/bash
HADOOP_HOME=/opt/module/hadoop-3.3.6
CFG=$HADOOP_HOME/etc/hadoop

# 1. hadoop-env.sh
sed -i 's/# export JAVA_HOME=.*/export JAVA_HOME=\/usr\/lib\/jvm\/java-8-openjdk-amd64/' $CFG/hadoop-env.sh
sed -i 's/# export HADOOP_HOME=.*/export HADOOP_HOME=\/opt\/module\/hadoop-3.3.6/' $CFG/hadoop-env.sh

# 2. core-site.xml
cat > $CFG/core-site.xml << 'XMLEOF'
<configuration>
<property><name>fs.defaultFS</name><value>hdfs://localhost:9000</value></property>
<property><name>hadoop.tmp.dir</name><value>/opt/module/hadoop-3.3.6/data/tmp</value></property>
</configuration>
XMLEOF

# 3. hdfs-site.xml
cat > $CFG/hdfs-site.xml << 'XMLEOF'
<configuration>
<property><name>dfs.replication</name><value>1</value></property>
<property><name>dfs.namenode.name.dir</name><value>/opt/module/hadoop-3.3.6/data/namenode</value></property>
<property><name>dfs.datanode.data.dir</name><value>/opt/module/hadoop-3.3.6/data/datanode</value></property>
</configuration>
XMLEOF

# 4. mapred-site.xml
cat > $CFG/mapred-site.xml << 'XMLEOF'
<configuration>
<property><name>mapreduce.framework.name</name><value>yarn</value></property>
</configuration>
XMLEOF

# 5. yarn-site.xml
cat > $CFG/yarn-site.xml << 'XMLEOF'
<configuration>
<property><name>yarn.nodemanager.aux-services</name><value>mapreduce_shuffle</value></property>
<property><name>yarn.nodemanager.vmem-check-enabled</name><value>false</value></property>
<property><name>yarn.nodemanager.pmem-check-enabled</name><value>false</value></property>
<property><name>yarn.nodemanager.resource.memory-mb</name><value>4096</value></property>
</configuration>
XMLEOF

# 6. workers
echo "localhost" > $CFG/workers

# 7. Create data dirs
mkdir -p $HADOOP_HOME/data/tmp $HADOOP_HOME/data/namenode $HADOOP_HOME/data/datanode

echo "Hadoop configuration complete!"
