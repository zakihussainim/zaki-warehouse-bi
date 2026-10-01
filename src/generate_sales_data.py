import argparse
import csv
import random
import uuid
from datetime import date, timedelta

CORE_PRODUCTS = [
    ("SKU-001", "Steel Widget",   "Hardware",   12.50),
    ("SKU-002", "Copper Fitting", "Hardware",    8.75),
    ("SKU-003", "Safety Gloves",  "PPE",         6.20),
    ("SKU-004", "Hard Hat",       "PPE",        14.00),
    ("SKU-005", "Conveyor Belt",  "Machinery", 340.00),
]

EXTENDED_PRODUCTS = [
    ("SKU-006", "Pressure Gauge", "Instrumentation", 45.00),
    ("SKU-007", "Thermal Sensor", "Instrumentation", 62.50),
]

CORE_CUSTOMERS = [
    ("CUST-001", "Northgate Manufacturing", "Corporate"),
    ("CUST-002", "Vale Industrial Supplies", "Corporate"),
    ("CUST-003", "Fenwick Builders",         "Consumer"),
    ("CUST-004", "Ashcroft Engineering",     "Corporate"),
]

EXTENDED_CUSTOMERS = [
    ("CUST-005", "Harbourline Logistics", "Corporate"),
]

CORE_REGIONS = [
    ("North West",  "United Kingdom"),
    ("South East",  "United Kingdom"),
    ("Midlands",    "United Kingdom"),
]

EXTENDED_REGIONS = [
    ("Scotland", "United Kingdom"),
]


def generate_rows(count, include_extended, start_date):
    products = CORE_PRODUCTS + (EXTENDED_PRODUCTS if include_extended else [])
    customers = CORE_CUSTOMERS + (EXTENDED_CUSTOMERS if include_extended else [])
    regions = CORE_REGIONS + (EXTENDED_REGIONS if include_extended else [])

    rows = []
    for _ in range(count):
        product_sku, product_name, category, base_price = random.choice(products)
        customer_id, customer_name, segment = random.choice(customers)
        region_name, country = random.choice(regions)

        unit_price = round(base_price * random.uniform(0.9, 1.1), 2)
        quantity = random.randint(1, 20)
        transaction_date = start_date + timedelta(days=random.randint(0, 13))

        rows.append({
            "transaction_id": f"TXN-{uuid.uuid4().hex[:10]}",
            "full_date": transaction_date.isoformat(),
            "product_sku": product_sku,
            "product_name": product_name,
            "category": category,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "segment": segment,
            "region_name": region_name,
            "country": country,
            "quantity": quantity,
            "unit_price": unit_price,
        })
    return rows


def write_csv(rows, output_path):
    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic sales transaction data.")
    parser.add_argument("--count", type=int, default=50, help="Number of transactions to generate")
    parser.add_argument("--output", required=True, help="Output CSV file path")
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Include the extended product/customer/region pools (new dimension values)",
    )
    parser.add_argument(
        "--start-date",
        default=date.today().isoformat(),
        help="Earliest transaction date, YYYY-MM-DD (defaults to today)",
    )
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    rows = generate_rows(args.count, args.extended, start_date)
    write_csv(rows, args.output)

    print(f"Wrote {len(rows)} transactions to {args.output}")


if __name__ == "__main__":
    main()