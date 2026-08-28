[阶段八 调度目录 /opt/script/mall/scheduler]

部署步骤（WSL 端）：
  1. 拷贝脚本
       cp scheduler_lib.sh run_pipeline.sh daily_scheduler.sh mail_alert.sh install_cron.sh /opt/script/mall/scheduler/
       chmod +x /opt/script/mall/scheduler/*.sh

  2. 配置邮件告警（可选，不配置会自动降级为日志告警）
       vi /opt/script/mall/scheduler/mail_alert.sh
       # 改 SMTP_HOST / SMTP_USER / SMTP_PASS / MAIL_TO

  3. 安装邮件发送依赖（可选）
       apt install -y sendemail libio-socket-ssl-perl libnet-ssleay-perl

  4. 验证单天 DAG（先单步干跑一天，确认 OK 再装 cron）
       /opt/script/mall/scheduler/run_pipeline.sh 2026-08-21 --skip-mock
       # 看状态：ls /data/scheduler/state/2026-08-21/*.state.latest.json
       # 看日志：ls /data/logs/scheduler/2026-08-21/*.log

  5. 装到 cron（每天 00:30 自动跑 T-1）
       /opt/script/mall/scheduler/install_cron.sh
       crontab -l  # 验证

常用运行参数：
  run_pipeline.sh <dt> [--skip-mock] [--force]
    --skip-mock : 跳过造数（MySQL 业务库已有该天数据时）
    --force     : 忽略幂等标记，强制重跑（会清空当天 state）

目录说明：
  /data/scheduler/state/<dt>/*.state.latest.json  : 任务最新状态 (NEW/RUNNING/SUCCESS/FAILED/RETRY/SKIPPED)
  /data/scheduler/state/<dt>/*.state.jsonl        : 任务状态历史（JSONL，可做监控）
  /data/scheduler/lock/*.lock                      : 全局 DAG 锁（flock）
  /data/logs/scheduler/<dt>/<task>.log             : 每任务 stdout/stderr
