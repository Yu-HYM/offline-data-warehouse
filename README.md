# 电商离线数据仓库

> 基于 Hadoop + Hive 的电商离线数仓全链路项目，覆盖 ODS→DWD→DWS→ADS 四层数仓架构，含 Shell DAG 调度、邮件告警、Superset 可视化看板。

---

## 📌 项目简介

本项目模拟电商业务场景，从 MySQL 业务库出发，经过全量/增量同步、数据清洗、维度退化、汇总聚合、复杂指标计算，最终将 ADS 层指标导出回 MySQL 并通过 Superset 看板展示。

项目在单机伪分布式环境（WSL2 + Hadoop 3.3.6 + Hive 3.1.3）上完成九个阶段的全链路建设，覆盖了离线数仓从 0 到 1 的完整流程。

---

## 🏗️ 系统架构

```
Python 造数器 ──> MySQL 业务库(mall)
                      │
                      ├── Python ETL(全量/增量) ──> HDFS ODS 贴源层
                      │                                │
                      │                     Hive SQL 清洗(脱敏/去脏/维度退化)
                      │                                │
                      │                              DWD 明细层
                      │                                │
                      │                  Python 聚合 + ORC 装载(两段式)
                      │                                │
                      │                          DWS 汇总层(ORC+SNAPPY)
                      │                                │
                      │                  Hive SQL + Python 复杂指标(RFM)
                      │                                │
                      │                          ADS 指标层(ORC)
                      │                                │
                      └────────── 导出(幂等) <──────┘
                                                     │
                                             MySQL 指标库(mall_ads)
                                                     │
                                            Superset BI 看板(4 图表)

贯穿：Shell DAG 调度(cron 00:30 触发 T-1) + flock 锁 + 指数退避重试 + 邮件告警
```

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| HDFS | Hadoop | 3.3.6 |
| 数仓引擎 | Hive | 3.1.3 |
| 业务数据库 | MySQL | 8.0 |
| ETL 脚本 | Python | 3.10 |
| 数据同步 | DataX + 自研 Python ETL | - |
| 调度 | Shell DAG + cron + flock | - |
| 告警 | Shell + mail | - |
| 可视化 | Apache Superset | 4.x |
| 压缩格式 | ORC + SNAPPY | - |

---

## 📊 数仓分层架构

| 层级 | 说明 | 存储格式 | 核心表 |
|------|------|----------|--------|
| **ODS** | 贴源层，MySQL 全量/增量同步 | TEXTFILE 外部表 | `ods_order_info`, `ods_sku_info`, `ods_user_info` 等 |
| **DWD** | 明细层，脱敏/去脏/维度退化/SCD2拉链 | ORC 内部表 | `dwd_fact_order_detail` |
| **DWS** | 汇总层，按主题聚合 | ORC+SNAPPY 内部表 | `dws_trade_daily_summary` |
| **ADS** | 应用层，业务指标 | ORC 内部表 | `ads_trade_stats`, `ads_repurchase_rate`, `ads_user_rfm` |

### ADS 层三大核心指标

| 指标表 | 说明 | 核心字段 |
|--------|------|---------|
| `ads_trade_stats` | 每日交易事实 | dt, gmv, order_count, pay_user_count, avg_pay_amount |
| `ads_repurchase_rate` | 复购率 | dt, order_user_count, repurchase_user_count, repurchase_rate |
| `ads_user_rfm` | RFM 用户分层 | dt, user_id, r_score, f_score, m_score, rfm_label（8类） |

---

## ✨ 核心设计

### 1. 全量 + 增量同步
- 全量同步：每日全表覆盖（适用于维度表）
- 增量同步：按日期增量拉取（适用于事实表），支持断点续传

### 2. DWD 数据清洗
- 手机号脱敏、金额负值过滤、空值处理
- 维度退化：将常用维度字段退化到事实表
- SCD2 拉链表：处理维度缓慢变化

### 3. DWS 两段式装载
- `prepare` 阶段：Python 聚合计算写入 HDFS 临时目录
- `load` 阶段：Hive LOAD DATA 装载到 ORC 内部表
- SNAPPY 压缩列存，查询效率提升

### 4. ADS 复杂指标（Python 计算）
- 复购率：90天窗口内二次及以上下单用户占比
- RFM 分层：R(最近购买)/F(频次)/M(金额) 三维5档，8类用户标签
- 复杂 JOIN/窗口函数在 Hive 本地模式不稳定时，用 Python 直接计算写回 HDFS

### 5. Shell DAG 调度
```
mock_data → ods_sync → dwd_process → dws_prepare → dws_load_orc
    → ads_hive(trade_stats) + ads_py(repurchase+rfm) → ads_to_mysql
```
- `flock` 文件锁防止重复执行
- 指数退避重试（最多2次）
- 邮件告警通知失败
- cron 定时触发（每日 00:30 执行 T-1）

### 6. 幂等设计
- ADS 导出 MySQL 采用 `REPLACE INTO`，重复执行不产生脏数据
- 调度支持 `--force` 参数强制重跑指定日期

---

## 📂 项目结构

```
01-离线数仓项目/
├── mock_data.py              # 造数器（5张业务表 + 30天历史 + 增量/脏数据）
├── batch_sync.py             # DataX 全量同步
├── etl_sync.py               # Python ETL 增量同步
├── dwd_etl.py                # DWD 清洗脚本
├── dws_ads_etl.py            # DWS+ADS 加工（TEXTFILE 快速验证版）
├── dws_orc_etl.py            # DWS ORC 两段式装载
├── prepare_dws_data.py      # DWS 数据准备
├── load_dws.py              # DWS LOAD DATA 装载
├── ads_etl_py.py             # ADS 复杂指标（复购率 + RFM）
├── process_ads.py            # ADS 简单指标（GMV 等 Hive SQL）
├── export_ads_to_mysql.py   # ADS 导出 MySQL
├── create_*.sql              # 建表脚本（ODS/DWD/DWS/ADS）
├── scheduler/                # 调度模块
│   ├── run_pipeline.sh       # DAG 入口（8步流水线）
│   ├── scheduler_lib.sh     # 调度公共库（锁/重试/日志/状态）
│   ├── mail_alert.sh        # 邮件告警
│   └── daily_scheduler.sh   # cron 定时入口
├── setup_hadoop.sh          # Hadoop 环境初始化
├── hive-site.xml            # Hive 配置
├── setup_superset_datasource.py  # Superset 数据源配置
├── 01-离线数仓项目操作文档.md
└── 离线数仓项目面试问答手册.md
```

---

## 🚀 快速开始

### 环境要求

- WSL2 Ubuntu 22.04（或 Linux 环境）
- Hadoop 3.3.6 + Hive 3.1.3
- MySQL 8.0
- Python 3.10+
- Apache Superset

### 部署步骤

```bash
# 1. 部署脚本到 WSL
bash scheduler/deploy_to_wsl.sh

# 2. 初始化 Hadoop + Hive 环境
bash setup_hadoop.sh

# 3. 创建业务库 + 造数
python3 mock_data.py
python3 setup_test_data.py

# 4. 建表（ODS → DWD → DWS → ADS）
hive -f create_ods_external_tables.sql
hive -f create_dwd_tables.sql
hive -f create_dws_ads_tables.sql

# 5. 执行全链路 DAG
bash scheduler/run_pipeline.sh 2026-08-19

# 6. 查看结果
mysql -uroot -p123456 -e "SELECT * FROM mall_ads.ads_trade_stats;"
```

### 调度配置

```bash
# 安装 cron 定时任务（每日 00:30 触发 T-1）
bash scheduler/install_cron.sh

# 手动重跑某天
bash scheduler/run_pipeline.sh 2026-08-20 --force
```

---

## 📈 Superset 看板

项目最终在 Superset 中构建了 4 个图表的看板：

| 图表 | 类型 | 数据源 |
|------|------|--------|
| 每日 GMV 趋势 | 折线图 | ads_trade_stats |
| 客单价变化 | 柱状图 | ads_trade_stats |
| 复购率趋势 | 折线图 | ads_repurchase_rate |
| RFM 用户分布 | 饼图 | ads_user_rfm |

访问地址：`http://localhost:8088`（admin / admin123）

---

## 🧠 设计亮点

1. **完整四层数仓架构**：ODS→DWD→DWS→ADS 标准分层，每层职责清晰。
2. **两段式装载**：prepare + load 分离，避免 Hive INSERT 性能瓶颈。
3. **Python 补位复杂计算**：Hive 本地模式跑不稳定的复杂 JOIN/窗口函数，用 Python 直接计算写回 HDFS，再通过外部表加载。
4. **DAG 调度工程化**：flock 锁、指数退避重试、邮件告警、状态持久化，生产级设计。
5. **幂等全链路**：所有环节支持重复执行，重跑不产生脏数据。

---

## 📝 License

MIT License
