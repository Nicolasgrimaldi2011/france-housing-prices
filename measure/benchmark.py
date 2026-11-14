import os
import psycopg
import time

def average_time(sql):
    times = []
    for _ in range(3):
        start = time.perf_counter()
        connection.execute(sql).fetchall()
        times.append(time.perf_counter() - start)
    return sum(times) / len(times)

connection = psycopg.connect(
    host="db",
    port=5432,
    user= os.environ["POSTGRES_USER"],
    dbname= os.environ["POSTGRES_DB"],
    password= os.environ["POSTGRES_PASSWORD"],
)
connection.autocommit = True

rows_sales = connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
rows_clean = connection.execute("SELECT COUNT(*) FROM clean_sales").fetchone()[0]

print("Rows in sales:", rows_sales)
print("Rows in clean_sales:", rows_clean)

years = [int(y) for y in os.environ["YEARS"].split(",")]
files_bytes = sum(os.path.getsize(f"/data/ValeursFoncieres-{y}.txt") for y in years)
db_bytes = connection.execute("SELECT pg_database_size(current_database())").fetchone()[0]
sales_bytes = connection.execute("SELECT pg_total_relation_size('sales')").fetchone()[0]
clean_bytes = connection.execute("SELECT pg_total_relation_size('clean_sales')").fetchone()[0]

print()
print("Original text files:", round(files_bytes / 1_000_000), "MB")
print("Database (total):", round(db_bytes / 1_000_000), "MB")
print("  table sales:", round(sales_bytes / 1_000_000), "MB")
print("  table clean_sales:", round(clean_bytes / 1_000_000), "MB")

ONE_CITY_QUERY = """
    SELECT year, COUNT(*), percentile_cont(0.5) WITHIN GROUP (ORDER BY price_m2)
    FROM clean_sales
    WHERE insee_code = '13201'
    GROUP BY year
"""

connection.execute("DROP INDEX IF EXISTS idx_clean_sales_insee")
without_index = average_time(ONE_CITY_QUERY)

connection.execute("CREATE INDEX idx_clean_sales_insee ON clean_sales (insee_code)")
connection.execute("ANALYZE clean_sales")
with_index = average_time(ONE_CITY_QUERY)

print()
print("One-city query, without index:", round(without_index * 1000, 1), "ms")
print("One-city query, with index:", round(with_index * 1000, 1), "ms")
print("The index makes the query", round(without_index / with_index), "times faster")

connection.close()

