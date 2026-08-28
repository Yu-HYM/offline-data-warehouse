#!/usr/bin/env bash
# ==========================================================================
# 邮件告警脚本 mail_alert.sh <level> <dt> <task> <msg>
# 占位配置：填入真实 SMTP 信息后即可工作
# 依赖：sendemail(apt install -y sendemail libio-socket-ssl-perl libnet-ssleay-perl)
# ==========================================================================
LEVEL="$1"; DT="$2"; TASK="$3"; shift 3; MSG="$*"

# ========== TODO 配置区（把 xxx 换成真实值）==========
SMTP_HOST="smtp.qq.com"        # 如 smtp.qq.com / smtp.163.com
SMTP_PORT="465"                 # 465=SSL  25=plain  587=STARTTLS
SMTP_USER="your_account@qq.com" # 发件邮箱
SMTP_PASS="your_auth_code"      # 邮箱授权码（非登录密码）
MAIL_FROM="DW调度 <${SMTP_USER}>"
MAIL_TO="receiver@example.com"  # 收件人，多个逗号分隔
MAIL_TITLE_PREFIX="[数仓告警]"
# ====================================================

# 未配置时自动降级
if [[ "$SMTP_USER" == *"your_account"* ]] || [[ "$SMTP_PASS" == *"your_auth_code"* ]] || [[ "$MAIL_TO" == *"example"* ]]; then
  echo "[mail_alert] 未配置 SMTP 账号，已降级为日志。dt=${DT} task=${TASK} level=${LEVEL} msg=${MSG}"
  exit 0
fi

which sendemail >/dev/null 2>&1 || {
  echo "[mail_alert] sendemail 未安装，请先执行: apt install -y sendemail libio-socket-ssl-perl libnet-ssleay-perl"
  exit 1
}

BODY=$(cat <<EOF
【告警级别】${LEVEL}
【调度日期】${DT}
【任务名称】${TASK}
【告警内容】${MSG}
【主机】$(hostname)
【时间】$(date '+%Y-%m-%d %H:%M:%S')
EOF
)

sendemail -f "$MAIL_FROM" \
  -t "$MAIL_TO" \
  -u "${MAIL_TITLE_PREFIX}[${LEVEL}] ${TASK} dt=${DT}" \
  -m "$BODY" \
  -s "${SMTP_HOST}:${SMTP_PORT}" \
  -o tls=yes \
  -xu "$SMTP_USER" \
  -xp "$SMTP_PASS" >/dev/null
echo "[mail_alert] send rc=$? dt=${DT} task=${TASK}"
