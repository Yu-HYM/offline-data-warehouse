DROP TABLE IF EXISTS mall.order_detail;
DROP TABLE IF EXISTS mall.order_info;
DROP TABLE IF EXISTS mall.payment_info;
DROP TABLE IF EXISTS mall.user_info;
DROP TABLE IF EXISTS mall.sku_info;

CREATE TABLE mall.user_info(
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
  login_name VARCHAR(20) COMMENT '登录名',
  nick_name VARCHAR(20) COMMENT '昵称',
  phone VARCHAR(11) COMMENT '手机号',
  gender TINYINT COMMENT '性别 0女 1男',
  user_level TINYINT COMMENT '用户等级 1-3',
  create_time DATETIME COMMENT '创建时间',
  operate_time DATETIME COMMENT '操作时间'
) COMMENT '用户信息表';

CREATE TABLE mall.sku_info(
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'SKU ID',
  sku_name VARCHAR(100) COMMENT '商品名称',
  category3_id BIGINT COMMENT '三级分类ID',
  price DECIMAL(10,2) COMMENT '价格',
  create_time DATETIME COMMENT '创建时间',
  operate_time DATETIME COMMENT '操作时间'
) COMMENT '商品SKU表';

CREATE TABLE mall.order_info(
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '订单ID',
  user_id BIGINT COMMENT '用户ID',
  total_amount DECIMAL(10,2) COMMENT '订单总金额',
  status TINYINT COMMENT '订单状态 1已支付 2已取消',
  create_time DATETIME COMMENT '创建时间',
  operate_time DATETIME COMMENT '操作时间'
) COMMENT '订单主表';

CREATE TABLE mall.order_detail(
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '明细ID',
  order_id BIGINT COMMENT '订单ID',
  sku_id BIGINT COMMENT 'SKU ID',
  sku_num INT COMMENT '购买数量',
  sku_price DECIMAL(10,2) COMMENT '商品单价',
  create_time DATETIME COMMENT '创建时间'
) COMMENT '订单明细表';

CREATE TABLE mall.payment_info(
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '支付ID',
  order_id BIGINT COMMENT '订单ID',
  pay_amount DECIMAL(10,2) COMMENT '支付金额',
  pay_status TINYINT COMMENT '支付状态 1已支付',
  create_time DATETIME COMMENT '创建时间',
  operate_time DATETIME COMMENT '操作时间'
) COMMENT '支付信息表';
