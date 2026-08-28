DROP TABLE IF EXISTS mall.user_info;
CREATE EXTERNAL TABLE mall.user_info (
  user_id BIGINT,
  user_name STRING,
  age INT,
  gender STRING,
  city STRING,
  create_time STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 'hdfs://localhost:9000/warehouse/mall/user_info';

DROP TABLE IF EXISTS mall.product_info;
CREATE EXTERNAL TABLE mall.product_info (
  product_id BIGINT,
  product_name STRING,
  category STRING,
  price DECIMAL(10,2),
  stock INT,
  create_time STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 'hdfs://localhost:9000/warehouse/mall/product_info';

DROP TABLE IF EXISTS mall.order_info;
CREATE EXTERNAL TABLE mall.order_info (
  order_id BIGINT,
  user_id BIGINT,
  product_id BIGINT,
  quantity INT,
  amount DECIMAL(10,2),
  order_status STRING,
  create_time STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 'hdfs://localhost:9000/warehouse/mall/order_info';
