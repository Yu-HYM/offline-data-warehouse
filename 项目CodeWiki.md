# 项目一 电商离线数仓 Code Wiki

面向开发者的代码库百科：模块地图、脚本结构、数据模型、调用关系与二次开发指南。运行查收步骤见 [01-离线数仓项目操作文档.md](file:///e:/简历项目/01-离线数仓项目/01-离线数仓项目操作文档.md)，面试问答见 [离线数仓项目面试问答手册.md](file:///e:/简历项目/01-离线数仓项目/离线数仓项目面试问答手册.md)。

## 1 项目定位

从 MySQL 业务库抽取电商订单数据，经 ODS → DWD → DWS → ADS 四层加工，产出 GMV、复购率、RFM 用户分层三类指标，落到 MySQL 指标库供 Superset 看板消费。全程由 Shell DAG 调度驱动，按天幂等运行。

| 层 | 技术 | 版本 |
|---|---|---|
| 存储与计算 | Hadoop（HDFS + YARN 伪分布式） | 3.3.6 |
| 数仓引擎 | Hive（Metastore 存 MySQL） | 3.1.3 |
| 业务库 / 指标库 / 元数据库 | MySQL | 8.0 |
| ETL 与加工 | Python（pymysql + subprocess 调 hive/hdfs） | 3.10 |
| 调度 | Bash + cron + flock | - |
| 可视化 | Apache Superset | 4.x |

## 2 代码库地图

源码在 Windows 侧维护，部署脚本 [deploy_to_wsl.sh](file:///e:/简历项目/01-离线数仓项目/scheduler/deploy_to_wsl.sh) 将其分发到 WSL 的 `/opt/script/mall/` 按子目录归位。运行时以 WSL 侧为准。

```
E:\简历项目\01-离线数仓项目\          源码（Windows）
│
├── mock_data.py                 造数器              → /opt/script/mall/mock/
├── etl_sync.py                  ODS 单表同步        → /opt/script/mall/datax/
├── batch_sync.py                ODS 批量同步入口    → /opt/script/mall/datax/
├── dwd_etl.py                   DWD 清洗加工        → /opt/script/mall/dwd/
├── prepare_dws_data.py          DWS 聚合到 HDFS     → /opt/script/mall/dws_orc/
├── load_dws.py                  DWS ORC 装载        → /opt/script/mall/dws_orc/
├── process_ads.py               ADS Hive 指标       → /opt/script/mall/ads/
├── ads_etl_py.py                ADS Python 指标     → /opt/script/mall/ads/
├── export_ads_to_mysql.py       ADS 导出 MySQL      → /opt/script/mall/ads/
├── setup_superset_datasource.py 看板自动化配置
├── verify_superset.py           看板 API 验证
├── start_services.sh            环境一键启动
├── create_*.sql / *.sql         各层建表与校验 SQL
└── scheduler/                   调度全家桶          → /opt/script/mall/scheduler/
    ├── scheduler_lib.sh         调度工具库（锁/状态/重试/告警）
    ├── run_pipeline.sh          单日 DAG 入口
    ├── daily_scheduler.sh       cron 触发器（T-1）
    ├── mail_alert.sh            邮件告警
    └── install_cron.sh          cron 安装
```

`scheduler/` 下另有 30 余个 `x_*.sh` 临时调试脚本，与正式流程无关，可在确认后清理。

## 3 数据流与模块调用链

```
                     ┌─────────────────────────────────────────────────┐
                     │ run_pipeline.sh <dt>  （9 步 DAG，见 §5）        │
                     └─────────────────────────────────────────────────┘
  步骤      脚本                      数据去向
  01  mock_data.py day        MySQL mall（5 业务表，含可控脏数据）
  02  batch_sync.py            MySQL → HDFS /warehouse/mall/ods/*（dt 分区）
  03  dwd_etl.py               MySQL → HDFS /warehouse/mall/dwd/*（清洗+维度退化）
  04  prepare_dws_data.py      MySQL 聚合 → HDFS /warehouse/mall/dws_load/*
  05  load_dws.py              临时外部表 → dws_trade_*_1d（ORC+SNAPPY 内部表）
  06  process_ads.py           DWS → ads_trade_stats（Hive 本地模式）
  07  ads_etl_py.py            MySQL → HDFS ads_load → ADS ORC（复购率+RFM）
  08  export_ads_to_mysql.py   Hive ADS → MySQL mall_ads（幂等 UPSERT）
  09  verify（内嵌 Python）     查 mall_ads 三表回读校验
```

模块间不直接调用函数，一律通过 DAG 编排：每个脚本独立接收 `dt` 参数、独立落盘，失败互不污染。这是整套代码最重要的架构决策——**脚本之间只共享数据契约（HDFS 路径 + 表结构），不共享代码**。

## 4 模块详解

### 4.1 造数器 mock_data.py

[源码](file:///e:/简历项目/01-离线数仓项目/mock_data.py)

```bash
python3 mock_data.py init 2026-08-19   # 生成 30 天历史（07-21 ~ 08-19）
python3 mock_data.py day 2026-08-20    # 增量生成单日
```

直连 MySQL `mall` 库，产出 5 张业务表：user_info、sku_info、order_info、order_detail、payment_info。

| 函数 | 职责 |
|---|---|
| `rand_dt(day)` | 生成指定日期内的随机时分秒 |
| `maybe_dirty(v, max_len)` | 脏数据注入：2% 概率返回 None，1.5% 返回负值/非法时间/短脏串 |
| `gen_users(day, n)` 等 5 个 gen_* | 各表数据生成，字段全部过 `maybe_dirty` |

设计意图：脏数据是**故意造的**——空手机号约 24 条、负金额订单约 113 条，作为 DWD 清洗逻辑的输入素材。面试讲解时这是"数据质量意识"的现成证据。

### 4.2 ODS 同步 etl_sync.py / batch_sync.py

[etl_sync.py](file:///e:/简历项目/01-离线数仓项目/etl_sync.py) 是单表同步器，等效替代 DataX：

```bash
python3 etl_sync.py sync user_info full 2026-08-19
python3 etl_sync.py sync order_info incr 2026-08-20
python3 etl_sync.py log 2026-08-20    # 埋点日志入 HDFS
```

同步策略集中在模块级常量 `SYNC_CONFIG`，每表一条：

| 表 | 模式 | 分区键 |
|---|---|---|
| user_info | full | operate_time |
| sku_info | full | - |
| order_info | incr | create_time |
| order_detail | incr | create_time |
| payment_info | incr | create_time |

执行链路：pymysql 抽取 → 本地 `/tmp/etl_sync` 写 TSV → `hdfs dfs -put` 到 `/warehouse/mall/ods/<hdfs_dir>/dt=<dt>/` → Hive 外部表自动可读。增量按分区键的日期过滤 WHERE 条件。

[batch_sync.py](file:///e:/简历项目/01-离线数仓项目/batch_sync.py) 是循环包装：按日期范围批量调 etl_sync，DAG 第 2 步的入口（`python3 batch_sync.py <dt> <dt>`）。

### 4.3 DWD 清洗 dwd_etl.py

[源码](file:///e:/简历项目/01-离线数仓项目/dwd_etl.py)

```bash
python3 dwd_etl.py 2026-08-19          # 增量单日
python3 dwd_etl.py 2026-08-19 --init   # 首日全量
```

| 函数 | 职责 |
|---|---|
| `hdfs_cmd(args)` | subprocess 包装 `hdfs dfs`，先 `source ~/.profile` 拿环境变量 |
| `mysql_query(sql)` / `mysql_execute(sql)` | 短连接式 MySQL 读写 |
| `mask_phone(phone)` | 脱敏：None 或长度≠11 → `00000000000`；否则 `151****6474` 格式 |
| `clean_gender(gender_str)` | 字符串性别归一为数字 |

产出 4 张表：`dim_user_full`（SCD2 拉链）、`dim_sku_full`、`fact_order_detail`、`fact_payment_detail`。清洗规则四条：手机号脱敏、空值兜底、负金额过滤（业务库 113 条负订单在此清零）、维度退化（事实表冗余用户昵称/商品名/品类名，下游免 JOIN）。

### 4.4 DWS 两段式装载 prepare_dws_data.py + load_dws.py

**第一段** [prepare_dws_data.py](file:///e:/简历项目/01-离线数仓项目/prepare_dws_data.py)：MySQL 侧完成 5 表 JOIN 聚合（order_info + order_detail + payment_info + user_info + sku_info），结果写 TSV 上传 `/warehouse/mall/dws_load/`。核心函数 `prepare_data(dt)` 内是两条大 SQL（用户宽表、商品宽表），聚合口径直接在 SQL 里完成。

**第二段** [load_dws.py](file:///e:/简历项目/01-离线数仓项目/load_dws.py)：Hive 侧完成格式转换。流程固定五步：

1. `DROP TABLE IF EXISTS tmp_user_dws_text` / `tmp_sku_dws_text`
2. 建临时外部表（TEXTFILE，`LOCATION '/warehouse/mall/dws_load/user|sku'`）
3. `ALTER TABLE ... ADD PARTITION (dt=...)`
4. `INSERT OVERWRITE TABLE dws_trade_user_order_1d SELECT ... FROM tmp_user_dws_text`
5. COUNT 验证行数

为什么分两段：绕开 Hive 处理多表 JOIN 时的本地模式内存限制——聚合下推到 MySQL（单机小数据量下更快更稳），Hive 只做纯格式转换。临时表每次 DROP 重建，天然幂等。

### 4.5 ADS 指标加工（双引擎）

**Hive 引擎** [process_ads.py](file:///e:/简历项目/01-离线数仓项目/process_ads.py)：处理简单单表聚合。

```python
run_hive_sql(hive_sql, tag)          # SQL 写临时文件 → hive -f → grep 过滤输出
process_ads_trade_stats(dt)          # INSERT OVERWRITE ads_trade_stats
                                      # FROM dws_trade_user_order_1d WHERE dt=
```

GMV、订单数、支付用户数、客单价一条 SQL 出全。执行前 `SET hive.exec.mode.local.auto=true` 走本地模式。

**Python 引擎** [ads_etl_py.py](file:///e:/简历项目/01-离线数仓项目/ads_etl_py.py)：处理 Hive 本地模式跑不稳的复杂指标（多阶段 JOIN、窗口分桶），复购率和 RFM 走这条路。

| 函数 | 职责 |
|---|---|
| `write_hdfs_text(rows, table, dt)` | 结果写 TSV → put 到 `/warehouse/mall/ads_load/<table>/dt=` |
| `ntile5(pairs)` | 等价 Hive NTILE(5)：按 value 升序切 5 档，value 越大分越高 |
| `load_to_orc(table, dt)` | 临时外部表 → INSERT OVERWRITE ADS ORC 表 |

RFM 口径：R（最近一次下单距今天数）、F（30 天下单次数）、M（30 天消费金额）各 5 档，组合映射 8 类标签（重要价值/重要保持/重要发展/重要挽留/一般价值/一般保持/一般发展/一般挽留）。

### 4.6 ADS 导出 export_ads_to_mysql.py

[源码](file:///e:/简历项目/01-离线数仓项目/export_ads_to_mysql.py)

```bash
python3 export_ads_to_mysql.py 2026-08-19 2026-08-20   # 支持多日期
```

| 函数 | 职责 |
|---|---|
| `hive_query(sql)` | hive 查询 → 二维数组。**关键实现**：SQL 写临时文件用 `hive -f`（规避 bash 引号嵌套与中文路径坑），显式注入完整 JAVA_HOME/HADOOP_HOME/HIVE_HOME/PATH 环境变量，逐行过滤 Hive 输出噪声（SLF4J/Time taken/fetched 等），`NULL`/空串统一转 None |
| `create_mysql_tables()` | 幂等建 mall_ads 库 + 3 表 |
| `batch_insert(table, columns, rows)` | executemany 批量写 + `ON DUPLICATE KEY UPDATE`，重跑不产生重复行 |
| `export_trade_stats(dates)` 等 3 个 | 各表按日期循环查询、汇总、批量写入 |

主键设计决定幂等语义：ads_trade_stats / ads_repurchase_rate 以 dt 为主键（每日一行，覆盖更新），ads_user_rfm 以 (dt, user_id) 为复合主键（每日快照）。

### 4.7 调度系统 scheduler/

**[scheduler_lib.sh](file:///e:/简历项目/01-离线数仓项目/scheduler/scheduler_lib.sh)** 工具库，被 source 引入：

| 函数 | 职责 |
|---|---|
| `task_log(task, dt, level, msg)` | 日志同时输出终端 + `/data/logs/scheduler/<dt>/<task>.log` |
| `acquire_lock(name, timeout)` | flock 文件锁（fd 9），dt 粒度防并发重入 |
| `release_lock()` | 关闭 fd 释放锁 |
| `write_state(task, dt, state, extra)` | 状态追加 JSONL + 覆盖 latest.json；state 取值 NEW/RUNNING/SUCCESS/FAILED/RETRY/SKIPPED |
| `read_latest_state` / `is_task_success` / `skip_if_success` | 断点续跑判断 |
| `run_with_retry(task, dt, max_retry, cmd)` | 执行命令，失败按 `backoff=(10 30 60 120 300)` 指数退避重试 |

**[run_pipeline.sh](file:///e:/简历项目/01-离线数仓项目/scheduler/run_pipeline.sh)** 单日 DAG 入口：

```bash
run_pipeline.sh 2026-08-22 [--skip-mock] [--force]
```

内部结构：`dag_step()` 统一封装"已成功则跳过（SKIPPED）→ 未成功则带重试执行 → 重试耗尽则 `fail_exit()` 发 CRITICAL 告警"三段逻辑。9 步顺序见 §3 流程图。锁名为 `pipeline_mall_<YYYYMMDD>`。脚本头部显式 export JAVA/HADOOP/HIVE 环境变量并追加 `HADOOP_CLASSPATH=$(hadoop classpath)`——后者是修复 YARN 报 MRAppMaster 找不到的关键。

**[daily_scheduler.sh](file:///e:/简历项目/01-离线数仓项目/scheduler/daily_scheduler.sh)**：cron 每日 00:30 触发，参数 `1` 表示跑 T-1，内部调 run_pipeline.sh。

**[mail_alert.sh](file:///e:/简历项目/01-离线数仓项目/scheduler/mail_alert.sh)**：SMTP SSL 465 + sendemail 发信；SMTP 四项配置未填时自动降级为日志告警。

### 4.8 可视化 setup_superset_datasource.py / verify_superset.py

[setup_superset_datasource.py](file:///e:/简历项目/01-离线数仓项目/setup_superset_datasource.py) 用 Superset ORM 直接建对象，不点 Web UI：

```
Database(mall_ads) → SqlaTable ×3（fetch_metadata() 同步列信息）
→ Slice ×4（line×2 / pie / big_number）→ Dashboard（position_json 定义 GRID/ROW/CHART 布局）
```

全程幂等：每步先 query 存在性再创建。

[verify_superset.py](file:///e:/简历项目/01-离线数仓项目/verify_superset.py) 走 API 全链路验证：JWT 登录 → 取 CSRF → dashboard/chart 列表 → `POST /api/v1/chart/data` 拉真实数据。两个 API 契约注意点：`datasource` 必须放 payload **顶层**（不能塞在 queries 里）；`time_range` 格式必须是 `100 years ago : now`（带 ago）。

## 5 数据模型速查

### Hive 侧（库 mall）

| 层 | 表 | 存储 | 说明 |
|---|---|---|---|
| ODS | ods_user_info / ods_sku_info / ods_order_info / ods_order_detail / ods_payment_info | 外部表 TEXTFILE | 贴源，dt 分区 |
| DWD | dim_user_full | 外部表 | 用户 SCD2 拉链 |
| DWD | dim_sku_full | 外部表 | 商品维表 |
| DWD | fact_order_detail / fact_payment_detail | 外部表 | 清洗后事实表，含退化维度 |
| DWS | dws_trade_user_order_1d | **内部表 ORC+SNAPPY** | 用户交易日宽，10 字段 |
| DWS | dws_trade_sku_order_1d | **内部表 ORC+SNAPPY** | 商品交易日宽，10 字段 |
| ADS | ads_trade_stats | 内部表 ORC+SNAPPY | gmv / order_count / pay_user_count / avg_pay_amount |
| ADS | ads_repurchase_rate | 内部表 ORC+SNAPPY | order_user_count / repurchase_user_count / repurchase_rate |
| ADS | ads_user_rfm | 内部表 ORC+SNAPPY | user_id / r_score / f_score / m_score / rfm_label |

DWS 用户宽表字段：user_id, user_nick_name, user_level, gender, order_count_1d, order_amount_1d, pay_amount_1d, order_sku_count_1d, category_count_1d, avg_order_amount_1d（全部按天聚合）。商品宽表字段：sku_id, sku_name, category1~3_name, order_count_1d, sale_count_1d, sale_amount_1d, order_user_count_1d, avg_price_1d。

另有阶段五的 TEXTFILE 外部表版（dws_user_day_agg、ads_gmv_day 等），是 ORC 版之前的链路验证产物，保留作对照。

### MySQL 侧

| 库 | 表 | 主键 | 用途 |
|---|---|---|---|
| mall | 5 张业务表 | id | 造数器写入，业务源 |
| mall | metastore 相关表 | - | Hive 元数据 |
| mall_ads | ads_trade_stats | dt | 供 Superset 消费 |
| mall_ads | ads_repurchase_rate | dt | 同上 |
| mall_ads | ads_user_rfm | (dt, user_id) | 同上 |

## 6 建表 SQL 索引

| 文件 | 用途 |
|---|---|
| [stage2_create_tables.sql](file:///e:/简历项目/01-离线数仓项目/stage2_create_tables.sql) | MySQL 业务库建表 |
| [create_ods_external_tables.sql](file:///e:/简历项目/01-离线数仓项目/create_ods_external_tables.sql) | ODS 外部表 |
| [create_dwd_tables.sql](file:///e:/简历项目/01-离线数仓项目/create_dwd_tables.sql) | DWD 建表 |
| [create_dws_ads_tables.sql](file:///e:/简历项目/01-离线数仓项目/create_dws_ads_tables.sql) | 阶段五 TEXTFILE 版 |
| [create_dws_orc_tables.sql](file:///e:/简历项目/01-离线数仓项目/create_dws_orc_tables.sql) | 阶段六 DWS ORC 内部表 |
| [create_ads_tables.sql](file:///e:/简历项目/01-离线数仓项目/create_ads_tables.sql) | 阶段七 ADS ORC 表 |
| [setup_mysql.sql](file:///e:/简历项目/01-离线数仓项目/setup_mysql.sql) | MySQL 初始化 |

## 7 配置常量与运行环境

所有 Python 脚本共享同一套 MySQL 连接字面量（未抽公共配置，见 §9）：

```python
MYSQL_CONFIG = {'host': 'localhost', 'user': 'root',
                'password': '123456', 'database': 'mall', 'charset': 'utf8mb4'}
```

HDFS 路径约定：

| 常量 | 值 | 使用方 |
|---|---|---|
| ODS | `/warehouse/mall/ods` | etl_sync.py |
| DWD | `/warehouse/mall/dwd` | dwd_etl.py |
| DWS 中转 | `/warehouse/mall/dws_load/{user,sku}` | prepare_dws_data.py → load_dws.py |
| ADS 中转 | `/warehouse/mall/ads_load/<table>` | ads_etl_py.py |

WSL 侧 Java/Hadoop 环境变量由 run_pipeline.sh 头部统一 export；单独手工跑脚本时需先 `source ~/.profile`。

## 8 二次开发指南

**新增一张业务表**（如优惠券表）：

1. [stage2_create_tables.sql](file:///e:/简历项目/01-离线数仓项目/stage2_create_tables.sql) 加 DDL，[mock_data.py](file:///e:/简历项目/01-离线数仓项目/mock_data.py) 加 `gen_coupon()` 并挂到 init/day 分支
2. [etl_sync.py](file:///e:/简历项目/01-离线数仓项目/etl_sync.py) 的 `SYNC_CONFIG` 加一条（选 full 或 incr + 分区键）
3. ODS 建表 SQL 加外部表，DWD 视需要加清洗逻辑
4. 重跑 `run_pipeline.sh <dt> --force`

**新增一个 ADS 指标**：

1. 简单单表聚合 → 在 [process_ads.py](file:///e:/简历项目/01-离线数仓项目/process_ads.py) 加一个 `process_ads_xxx(dt)` 函数
2. 复杂 JOIN/窗口 → 在 [ads_etl_py.py](file:///e:/简历项目/01-离线数仓项目/ads_etl_py.py) 加函数，复用 `write_hdfs_text` + `load_to_orc`
3. [create_ads_tables.sql](file:///e:/简历项目/01-离线数仓项目/create_ads_tables.sql) 加表，[export_ads_to_mysql.py](file:///e:/简历项目/01-离线数仓项目/export_ads_to_mysql.py) 的 `create_mysql_tables()` 加 DDL + 加 export 函数
4. Superset 侧跑一次 setup 脚本或在 UI 建数据集

**新增一个调度步骤**：在 [run_pipeline.sh](file:///e:/简历项目/01-离线数仓项目/scheduler/run_pipeline.sh) 的 STEP 区块加一行 `dag_step "NN_task_name" "<command>"`，编号决定执行顺序。锁、状态落盘、重试、告警全部由 dag_step 自动获得，无需另写。

## 9 已知技术债

| 项 | 现状 | 影响 | 改法 |
|---|---|---|---|
| MySQL 配置重复 | 每个脚本各自硬编码 MYSQL_CONFIG | 改密码要动 8 个文件 | 抽 `config.py` 或读环境变量 |
| 告警占位 | mail_alert.sh 的 SMTP 四项未填真实值 | 失败告警降级为日志 | 填授权码即可启用 |
| 调试脚本堆积 | scheduler/ 下 30 余个 x_*.sh | 目录可读性差 | 确认后删除 |
| 单机伪分布式 | Hadoop 单节点 | 无法讲 HA/多副本实战 | 面试口径：资源受限，方案可平移 |

---

*生成于 2026-08-21，对应阶段一至九完整交付版本*
