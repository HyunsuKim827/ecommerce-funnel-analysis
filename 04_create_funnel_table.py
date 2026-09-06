"""
2019년 12월 세션-상품 단위 퍼널 데이터마트 구축

분석 단위:
- user_session × product_id

목적:
- View → Cart → Purchase 유효 경로를 분석 단위별로 저장
- 이후 세그먼트 및 EDA에서 반복적인 원본 로그 조회 방지
"""

import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(
    str(BASE_DIR / "ecommerce.duckdb")
)

con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")

print("DuckDB 연결 완료")

print("\nStep 2-1: View 테이블 생성 시작")

con.execute("""
    CREATE OR REPLACE TABLE funnel_view AS

    SELECT
        user_session,
        product_id,
        MIN(event_time) AS first_view

    FROM dec_events

    WHERE event_type = 'view'
      AND user_session IS NOT NULL

    GROUP BY
        user_session,
        product_id
""")

result = con.sql("""
    SELECT COUNT(*)
    FROM funnel_view
""").fetchone()

print("View 테이블 생성 완료")
print("행 수:", result[0])

con.close()

print("\nStep 2-2: Cart 테이블 생성 시작")

con.execute("""
    CREATE OR REPLACE TABLE funnel_cart AS

    SELECT
        v.user_session,
        v.product_id,
        v.first_view,
        MIN(c.event_time) AS first_valid_cart

    FROM funnel_view v

    LEFT JOIN dec_events c
        ON v.user_session = c.user_session
       AND v.product_id = c.product_id
       AND c.event_type = 'cart'
       AND c.event_time >= v.first_view

    GROUP BY
        v.user_session,
        v.product_id,
        v.first_view
""")

result = con.sql("""
    SELECT
        COUNT(*) AS total,
        COUNT(first_valid_cart) AS cart_count
    FROM funnel_cart
""").fetchone()

print("Cart 테이블 생성 완료")
print("전체 행 수:", result[0])
print("유효 Cart 수:", result[1])

con.close()

print("\nStep 2-3: Purchase 테이블 생성 시작")

con.execute("""
    CREATE OR REPLACE TABLE funnel_purchase AS

    SELECT
        fc.user_session,
        fc.product_id,
        fc.first_view,
        fc.first_valid_cart,
        MIN(p.event_time) AS first_valid_purchase

    FROM funnel_cart fc

    LEFT JOIN dec_events p
        ON fc.user_session = p.user_session
       AND fc.product_id = p.product_id
       AND p.event_type = 'purchase'
       AND p.event_time >= fc.first_valid_cart

    GROUP BY
        fc.user_session,
        fc.product_id,
        fc.first_view,
        fc.first_valid_cart
""")

result = con.sql("""
    SELECT
        COUNT(*) AS total,
        COUNT(first_valid_cart) AS cart_count,
        COUNT(first_valid_purchase) AS purchase_count
    FROM funnel_purchase
""").fetchone()

print("Purchase 테이블 생성 완료")
print("전체 행 수:", result[0])
print("유효 Cart 수:", result[1])
print("유효 Purchase 수:", result[2])

con.close()

print("\nStep 2-4: 최종 퍼널 데이터마트 생성 시작")

con.execute("""
    CREATE OR REPLACE TABLE funnel_session_product AS

    SELECT
        user_session,
        product_id,
        first_view,
        first_valid_cart,
        first_valid_purchase,

        CASE
            WHEN first_valid_cart IS NOT NULL THEN 1
            ELSE 0
        END AS cart_flag,

        CASE
            WHEN first_valid_purchase IS NOT NULL THEN 1
            ELSE 0
        END AS purchase_flag

    FROM funnel_purchase
""")

result = con.sql("""
    SELECT
        COUNT(*) AS total,
        SUM(cart_flag) AS cart_count,
        SUM(purchase_flag) AS purchase_count
    FROM funnel_session_product
""").fetchone()

print("최종 퍼널 데이터마트 생성 완료")
print("전체 행 수:", result[0])
print("Cart 전환 수:", result[1])
print("Purchase 전환 수:", result[2])

con.close()

print("\n===== 최종 데이터마트 구조 확인 =====")

print(
    con.sql("""
        DESCRIBE funnel_session_product
    """)
)

print("\n===== 샘플 5행 =====")

print(
    con.sql("""
        SELECT *
        FROM funnel_session_product
        LIMIT 5
    """)
)

con.close()

print("\n===== 첫 View 시점 상품 정보 확인 =====")

result = con.sql("""
    SELECT
        f.user_session,
        f.product_id,
        f.first_view,
        d.price,
        d.category_id,
        d.category_code,
        d.brand

    FROM funnel_session_product f

    JOIN dec_events d
        ON f.user_session = d.user_session
       AND f.product_id = d.product_id
       AND f.first_view = d.event_time
       AND d.event_type = 'view'

    LIMIT 5
""")

print(result)

con.close()