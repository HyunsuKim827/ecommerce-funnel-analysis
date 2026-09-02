import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(str(BASE_DIR / "ecommerce.duckdb"))

DATA_FILE = BASE_DIR / "2019-Dec.csv.gz"

print("12월 데이터를 DuckDB 테이블로 저장합니다.")

con.execute(f"""
    CREATE TABLE IF NOT EXISTS dec_events AS
    SELECT *
    FROM read_csv_auto('{DATA_FILE.as_posix()}')
""")

print("dec_events 테이블 생성 완료")

result = con.sql("""
    SELECT COUNT(*) AS total_rows
    FROM dec_events
""")

print(result)

con.close()