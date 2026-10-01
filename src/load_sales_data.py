import os
import time

import boto3

REDSHIFT_WORKGROUP = os.environ["REDSHIFT_WORKGROUP"]
REDSHIFT_DATABASE = os.environ["REDSHIFT_DATABASE"]
REDSHIFT_S3_ROLE_ARN = os.environ["REDSHIFT_S3_ROLE_ARN"]

redshift_data = boto3.client("redshift-data")

INCREMENTAL_LOAD_SQL = """
DELETE FROM stg_transactions;

COPY stg_transactions
FROM '{s3_path}'
IAM_ROLE '{redshift_s3_role_arn}'
FORMAT CSV
IGNOREHEADER 1;

INSERT INTO dim_product (product_sku, product_name, category)
SELECT DISTINCT s.product_sku, s.product_name, s.category
FROM stg_transactions s
LEFT JOIN dim_product d ON s.product_sku = d.product_sku
WHERE d.product_sku IS NULL;

INSERT INTO dim_customer (customer_id, customer_name, segment)
SELECT DISTINCT s.customer_id, s.customer_name, s.segment
FROM stg_transactions s
LEFT JOIN dim_customer d ON s.customer_id = d.customer_id
WHERE d.customer_id IS NULL;

INSERT INTO dim_region (region_name, country)
SELECT DISTINCT s.region_name, s.country
FROM stg_transactions s
LEFT JOIN dim_region d ON s.region_name = d.region_name
WHERE d.region_name IS NULL;

INSERT INTO dim_date (date_key, full_date, day_of_week, day_name, month_number, month_name, quarter, year)
SELECT DISTINCT
    CAST(TO_CHAR(s.full_date, 'YYYYMMDD') AS INT),
    s.full_date,
    TO_CHAR(s.full_date, 'ID'),
    TO_CHAR(s.full_date, 'Day'),
    EXTRACT(MONTH FROM s.full_date),
    TO_CHAR(s.full_date, 'Month'),
    EXTRACT(QUARTER FROM s.full_date),
    EXTRACT(YEAR FROM s.full_date)
FROM stg_transactions s
LEFT JOIN dim_date d ON CAST(TO_CHAR(s.full_date, 'YYYYMMDD') AS INT) = d.date_key
WHERE d.date_key IS NULL;

DELETE FROM fact_transactions
USING stg_transactions s
WHERE fact_transactions.transaction_id = s.transaction_id;

INSERT INTO fact_transactions (transaction_id, date_key, product_key, customer_key, region_key, quantity, unit_price, revenue)
SELECT
    s.transaction_id,
    CAST(TO_CHAR(s.full_date, 'YYYYMMDD') AS INT),
    p.product_key,
    c.customer_key,
    r.region_key,
    s.quantity,
    s.unit_price,
    s.quantity * s.unit_price
FROM stg_transactions s
JOIN dim_product  p ON s.product_sku  = p.product_sku
JOIN dim_customer c ON s.customer_id  = c.customer_id
JOIN dim_region   r ON s.region_name  = r.region_name;
"""


def run_sql_and_wait(sql):
    response = redshift_data.execute_statement(
        WorkgroupName=REDSHIFT_WORKGROUP,
        Database=REDSHIFT_DATABASE,
        Sql=sql,
    )
    statement_id = response["Id"]

    while True:
        status = redshift_data.describe_statement(Id=statement_id)
        state = status["Status"]
        if state == "FINISHED":
            return
        if state in ("FAILED", "ABORTED"):
            raise RuntimeError(f"Redshift statement {state}: {status.get('Error')}")
        time.sleep(1)


def handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]
    s3_path = f"s3://{bucket}/{key}"

    sql = INCREMENTAL_LOAD_SQL.format(
        s3_path=s3_path,
        redshift_s3_role_arn=REDSHIFT_S3_ROLE_ARN,
    )

    run_sql_and_wait(sql)

    print(f"Loaded {s3_path} into the warehouse.")

    return {"loaded_file": s3_path}
