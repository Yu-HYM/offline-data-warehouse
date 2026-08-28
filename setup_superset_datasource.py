#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_superset_datasource.py
阶段九：自动配置 Superset —— mall_ads 数据库 + 3 个数据集 + 4 张图表 + 1 个看板
在 superset venv 内、带 SUPERSET_CONFIG_PATH 环境变量执行
"""
import json
import sys

from superset.app import create_app

app = create_app()

def main():
    with app.app_context():
        from superset import db
        from superset.models.core import Database
        from superset.connectors.sqla.models import SqlaTable
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard

        # ============ 1. 数据库连接 ============
        d = db.session.query(Database).filter_by(database_name="mall_ads").first()
        if not d:
            d = Database(
                database_name="mall_ads",
                sqlalchemy_uri="mysql+pymysql://root:123456@localhost:3306/mall_ads?charset=utf8mb4",
                expose_in_sqllab=True,
                allow_ctas=False,
                allow_dml=False,
            )
            db.session.add(d)
            db.session.commit()
            print("[1] 数据库 mall_ads 已创建 id=%s" % d.id)
        else:
            print("[1] 数据库已存在 id=%s" % d.id)

        # ============ 2. 数据集 ============
        def make_dataset(table):
            t = db.session.query(SqlaTable).filter_by(table_name=table, database_id=d.id).first()
            if t:
                print("  数据集已存在: %s id=%s" % (table, t.id))
                return t
            t = SqlaTable(table_name=table, schema=None)
            t.database = d
            t.database_id = d.id
            db.session.add(t)
            db.session.flush()
            t.fetch_metadata()
            db.session.commit()
            print("  数据集已创建: %s id=%s cols=%s" % (table, t.id, [c.column_name for c in t.columns]))
            return t

        ds_trade = make_dataset("ads_trade_stats")
        ds_repurchase = make_dataset("ads_repurchase_rate")
        ds_rfm = make_dataset("ads_user_rfm")

        # ============ 3. 图表 ============
        def chart_params(ds, viz, groupby, metrics, extra=None):
            p = {
                "datasource": {"id": ds.id, "type": "table"},
                "viz_type": viz,
                "groupby": groupby,
                "metrics": metrics,
                "row_limit": 10000,
                "show_legend": True,
            }
            if extra:
                p.update(extra)
            return json.dumps(p)

        def simple_metric(col, agg="SUM", label=None):
            return {
                "expressionType": "SIMPLE",
                "column": {"column_name": col, "type": "NUMERIC"},
                "aggregate": agg,
                "label": label or ("%s(%s)" % (agg.lower(), col)),
            }

        charts = []

        # 图表1: GMV 订单趋势折线图
        c1 = db.session.query(Slice).filter_by(slice_name="GMV订单趋势").first()
        if not c1:
            c1 = Slice(
                slice_name="GMV订单趋势",
                viz_type="line",
                datasource_id=ds_trade.id,
                datasource_type="table",
                params=chart_params(
                    ds_trade, "line", ["dt"],
                    [simple_metric("gmv", "SUM", "GMV总额"), simple_metric("order_count", "SUM", "订单数")],
                    {"x_axis": "dt"},
                ),
            )
            db.session.add(c1)
            charts.append(c1)
            print("  图表已创建: GMV订单趋势")
        else:
            charts.append(c1)

        # 图表2: 复购率趋势
        c2 = db.session.query(Slice).filter_by(slice_name="复购率趋势").first()
        if not c2:
            c2 = Slice(
                slice_name="复购率趋势",
                viz_type="line",
                datasource_id=ds_repurchase.id,
                datasource_type="table",
                params=chart_params(
                    ds_repurchase, "line", ["dt"],
                    [simple_metric("repurchase_rate", "AVG", "复购率"), simple_metric("order_user_count", "SUM", "下单用户数")],
                    {"x_axis": "dt"},
                ),
            )
            db.session.add(c2)
            charts.append(c2)
            print("  图表已创建: 复购率趋势")
        else:
            charts.append(c2)

        # 图表3: RFM 用户分群饼图
        c3 = db.session.query(Slice).filter_by(slice_name="RFM用户分群").first()
        if not c3:
            c3 = Slice(
                slice_name="RFM用户分群",
                viz_type="pie",
                datasource_id=ds_rfm.id,
                datasource_type="table",
                params=chart_params(
                    ds_rfm, "pie", ["rfm_label"],
                    [{"expressionType": "SIMPLE", "column": {"column_name": "user_id", "type": "TEXT"}, "aggregate": "COUNT_DISTINCT", "label": "用户数"}],
                ),
            )
            db.session.add(c3)
            charts.append(c3)
            print("  图表已创建: RFM用户分群")
        else:
            charts.append(c3)

        # 图表4: GMV 日报大数字
        c4 = db.session.query(Slice).filter_by(slice_name="GMV日报").first()
        if not c4:
            c4 = Slice(
                slice_name="GMV日报",
                viz_type="big_number",
                datasource_id=ds_trade.id,
                datasource_type="table",
                params=chart_params(
                    ds_trade, "big_number", [],
                    [simple_metric("gmv", "SUM", "GMV")],
                    {"x_axis": "dt", "granularity_sqla": "dt", "time_grain_sqla": "P1D"},
                ),
            )
            db.session.add(c4)
            charts.append(c4)
            print("  图表已创建: GMV日报")
        else:
            charts.append(c4)

        db.session.commit()

        # ============ 4. Dashboard ============
        dash = db.session.query(Dashboard).filter_by(dashboard_title="电商离线数仓看板").first()
        if not dash:
            chart_ids = [c.id for c in charts]
            position = {
                "DASHBOARD_VERSION_KEY": "v2",
                "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
                "GRID_ID": {"id": "GRID_ID", "type": "GRID", "children": ["ROW-BN", "ROW-LINE", "ROW-PIE"]},
                "ROW-BN": {"type": "ROW", "id": "ROW-BN", "children": ["CHART-BN"]},
                "CHART-BN": {"type": "CHART", "id": "CHART-BN", "chartName": "GMV日报", "meta": {"chartId": chart_ids[3], "sliceName": "GMV日报", "width": 12}, "chartId": chart_ids[3]},
                "ROW-LINE": {"type": "ROW", "id": "ROW-LINE", "children": ["CHART-GMV", "CHART-RATE"]},
                "CHART-GMV": {"type": "CHART", "id": "CHART-GMV", "chartName": "GMV订单趋势", "meta": {"chartId": chart_ids[0], "sliceName": "GMV订单趋势", "width": 6}, "chartId": chart_ids[0]},
                "CHART-RATE": {"type": "CHART", "id": "CHART-RATE", "chartName": "复购率趋势", "meta": {"chartId": chart_ids[1], "sliceName": "复购率趋势", "width": 6}, "chartId": chart_ids[1]},
                "ROW-PIE": {"type": "ROW", "id": "ROW-PIE", "children": ["CHART-RFM"]},
                "CHART-RFM": {"type": "CHART", "id": "CHART-RFM", "chartName": "RFM用户分群", "meta": {"chartId": chart_ids[2], "sliceName": "RFM用户分群", "width": 12}, "chartId": chart_ids[2]},
            }
            dash = Dashboard(
                dashboard_title="电商离线数仓看板",
                slug="mall_dw",
                position_json=json.dumps(position),
            )
            dash.slices = charts
            db.session.add(dash)
            db.session.commit()
            print("[4] 看板已创建: 电商离线数仓看板 slug=mall_dw, charts=%s" % chart_ids)
        else:
            print("[4] 看板已存在 id=%s" % dash.id)

        print("\n=== 全部完成 ===")
        print("访问: http://localhost:8088  账号 admin / admin123")

if __name__ == "__main__":
    main()