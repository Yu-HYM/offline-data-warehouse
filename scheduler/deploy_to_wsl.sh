#!/usr/bin/env bash
# deploy_to_wsl.sh (在 WSL 内执行)
WIN='/mnt/e/简历项目/01-离线数仓项目'
sudo mkdir -p /opt/script/mall/dws_orc /opt/script/mall/ads /opt/script/mall/scheduler
sudo chown -R hadoop:hadoop /opt/script/mall/dws_orc /opt/script/mall/ads /opt/script/mall/scheduler

cp "$WIN/prepare_dws_data.py"    /opt/script/mall/dws_orc/
cp "$WIN/load_dws.py"            /opt/script/mall/dws_orc/
cp "$WIN/process_ads.py"         /opt/script/mall/ads/
cp "$WIN/ads_etl_py.py"          /opt/script/mall/ads/
cp "$WIN/export_ads_to_mysql.py" /opt/script/mall/ads/
cp "$WIN/batch_sync.py"          /opt/script/mall/datax/

for f in scheduler_lib.sh run_pipeline.sh daily_scheduler.sh mail_alert.sh install_cron.sh README_scheduler.txt; do
  cp "$WIN/scheduler/$f" /opt/script/mall/scheduler/
done
chmod +x /opt/script/mall/dws_orc/*.py /opt/script/mall/ads/*.py /opt/script/mall/scheduler/*.sh /opt/script/mall/datax/*.py

echo '--- dws_orc ---'; ls /opt/script/mall/dws_orc/
echo '--- ads ---';     ls /opt/script/mall/ads/
echo '--- scheduler ---'; ls /opt/script/mall/scheduler/
echo '--- datax batch ---'; ls /opt/script/mall/datax/ | grep batch
