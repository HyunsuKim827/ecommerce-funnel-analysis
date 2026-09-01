import duckdb
from pathlib import Path

# 이 Python 파일이 있는 폴더
BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(str(BASE_DIR / "ecommerce.duckdb"))

files = [
    "2019-Oct.csv.gz",
    "2019-Nov.csv.gz",
    "2019-Dec.csv.gz"
]

for file in files:
    file_path = BASE_DIR / file

    print(f"\n===== {file} =====")

    query = f"""
        SELECT
            COUNT(*) AS total_events,
            COUNT(DISTINCT user_id) AS users,
            COUNT(DISTINCT user_session) AS sessions,
            MIN(event_time) AS min_time,
            MAX(event_time) AS max_time
        FROM read_csv_auto('{file_path.as_posix()}')
    """

    result = con.sql(query)
    print(result)

    print("\n===== EVENT TYPE COMPARISON =====")

for file in files:
    file_path = BASE_DIR / file

    print(f"\n===== {file} =====")

    query = f"""
        SELECT
            event_type,
            COUNT(*) AS event_count,
            ROUND(
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
                2
            ) AS event_pct
        FROM read_csv_auto('{file_path.as_posix()}')
        GROUP BY event_type
        ORDER BY event_count DESC
    """

    print(con.sql(query))

print("\n===== DECEMBER DATA QUALITY CHECK =====")

dec_file = BASE_DIR / "2019-Dec.csv.gz"

query = f"""
    SELECT
        COUNT(DISTINCT product_id) AS products,

        COUNT(*) - COUNT(user_id) AS null_user_id,
        COUNT(*) - COUNT(user_session) AS null_session,
        COUNT(*) - COUNT(category_code) AS null_category_code,
        COUNT(*) - COUNT(brand) AS null_brand,
        COUNT(*) - COUNT(price) AS null_price,

        COUNT(*) FILTER (WHERE price <= 0) AS non_positive_price,

        MIN(price) AS min_price,
        MAX(price) AS max_price,
        ROUND(AVG(price), 2) AS avg_price

    FROM read_csv_auto('{dec_file.as_posix()}')
"""

print(con.sql(query))


print("\n===== DECEMBER EVENT TYPES =====")

query = f"""
    SELECT
        event_type,
        COUNT(*) AS event_count
    FROM read_csv_auto('{dec_file.as_posix()}')
    GROUP BY event_type
    ORDER BY event_count DESC
"""

print(con.sql(query))

con.close()