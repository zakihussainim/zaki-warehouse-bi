import boto3
import sys
import time


WORKGROUP_NAME = "zaki-warehouse-bi-dev-workgroup"
DATABASE_NAME = "salesdw"
REGION = "eu-west-2"


CHECKS = [
    (
        "No duplicate transaction_id in fact_transactions",
        """
        SELECT transaction_id, COUNT(*) AS occurrences
        FROM fact_transactions
        GROUP BY transaction_id
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "No fact rows with a product_key missing from dim_product",
        """
        SELECT f.product_key
        FROM fact_transactions f
        LEFT JOIN dim_product d ON f.product_key = d.product_key
        WHERE d.product_key IS NULL
        """,
    ),
    (
        "No fact rows with a customer_key missing from dim_customer",
        """
        SELECT f.customer_key
        FROM fact_transactions f
        LEFT JOIN dim_customer d ON f.customer_key = d.customer_key
        WHERE d.customer_key IS NULL
        """,
    ),
    (
        "No fact rows with a region_key missing from dim_region",
        """
        SELECT f.region_key
        FROM fact_transactions f
        LEFT JOIN dim_region d ON f.region_key = d.region_key
        WHERE d.region_key IS NULL
        """,
    ),
    (
        "No fact rows with a date_key missing from dim_date",
        """
        SELECT f.date_key
        FROM fact_transactions f
        LEFT JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.date_key IS NULL
        """,
    ),
    (
        "revenue always equals quantity * unit_price",
        """
        SELECT transaction_id, quantity, unit_price, revenue
        FROM fact_transactions
        WHERE revenue != quantity * unit_price
        """,
    ),
    (
        "fact_transactions is not empty",
        """
        SELECT 1
        WHERE (SELECT COUNT(*) FROM fact_transactions) = 0
        """,
    ),
]


def run_query(client, sql: str):

    submitted = client.execute_statement(
        WorkgroupName=WORKGROUP_NAME,
        Database=DATABASE_NAME,
        Sql=sql,
    )
    statement_id = submitted["Id"]

    while True:
        status = client.describe_statement(Id=statement_id)
        state = status["Status"]

        if state == "FINISHED":
            break
        if state in ("FAILED", "ABORTED"):
            error_message = status.get("Error", "no error message returned")
            raise RuntimeError(f"Query failed: {error_message}")

        time.sleep(1)  # avoid hammering the API while we wait

    result = client.get_statement_result(Id=statement_id)
    return result["Records"]


def main():
    client = boto3.client("redshift-data", region_name=REGION)

    failures = []

    for name, sql in CHECKS:
        print(f"Running check: {name}")
        try:
            rows = run_query(client, sql)
        except RuntimeError as e:
            print(f"  ERROR — could not run this check: {e}")
            failures.append(name)
            continue

        if rows:
            print(f"  FAILED — {len(rows)} offending row(s) found")
            failures.append(name)
        else:
            print("  passed")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed:")
        for name in failures:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"All {len(CHECKS)} checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()