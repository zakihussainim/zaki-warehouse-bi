CREATE TABLE dim_date (
    date_key      INT PRIMARY KEY,
    full_date     DATE NOT NULL,
    day_of_week   VARCHAR(10),
    day_name      VARCHAR(10),
    month_number  INT,
    month_name    VARCHAR(10),
    quarter       INT,
    year          INT
);

CREATE TABLE dim_product (
    product_key   INT IDENTITY(1,1) PRIMARY KEY,
    product_sku   VARCHAR(20) NOT NULL,
    product_name  VARCHAR(100),
    category      VARCHAR(50)
);

CREATE TABLE dim_customer (
    customer_key  INT IDENTITY(1,1) PRIMARY KEY,
    customer_id   VARCHAR(20) NOT NULL,
    customer_name VARCHAR(100),
    segment       VARCHAR(30)
);

CREATE TABLE dim_region (
    region_key    INT IDENTITY(1,1) PRIMARY KEY,
    region_name   VARCHAR(50) NOT NULL,
    country       VARCHAR(50)
);


CREATE TABLE fact_transactions (
    transaction_id  VARCHAR(30) NOT NULL,
    date_key        INT NOT NULL REFERENCES dim_date(date_key),
    product_key     INT NOT NULL REFERENCES dim_product(product_key),
    customer_key    INT NOT NULL REFERENCES dim_customer(customer_key),
    region_key      INT NOT NULL REFERENCES dim_region(region_key),
    quantity        INT NOT NULL,
    unit_price      DECIMAL(10,2) NOT NULL,
    revenue         DECIMAL(12,2) NOT NULL,
    loaded_at       TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE KEY
DISTKEY (date_key)
SORTKEY (date_key);


CREATE TABLE stg_transactions (
    transaction_id  VARCHAR(30),
    full_date       DATE,
    product_sku     VARCHAR(20),
    product_name    VARCHAR(100),
    category        VARCHAR(50),
    customer_id     VARCHAR(20),
    customer_name   VARCHAR(100),
    segment         VARCHAR(30),
    region_name     VARCHAR(50),
    country         VARCHAR(50),
    quantity        INT,
    unit_price      DECIMAL(10,2)
);
