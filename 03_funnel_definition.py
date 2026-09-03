"""
2019년 12월 고객 행동 로그 기반 전환 퍼널 분석

분석 단위:
- user_session × product_id

유효 전환 기준:
- View 이후 Cart가 발생해야 함
- 유효 Cart 이후 Purchase가 발생해야 함
- 반복 이벤트가 있더라도 시간 순서를 만족하는
  View → Cart → Purchase 경로가 존재하면 전환으로 인정
"""

import duckdb
from pathlib import Path


# 1. DuckDB 연결

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(
    str(BASE_DIR / "ecommerce.duckdb")
)

# 메모리 사용 완화
con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")

print("DuckDB 연결 완료")



# 2. 유효 전환 퍼널 계산

query = """
    WITH viewed AS (
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
    ),

    valid_cart AS (
        SELECT
            v.user_session,
            v.product_id,
            v.first_view,

            MIN(c.event_time) AS first_valid_cart

        FROM viewed v

        LEFT JOIN dec_events c
            ON v.user_session = c.user_session
           AND v.product_id = c.product_id
           AND c.event_type = 'cart'
           AND c.event_time >= v.first_view

        GROUP BY
            v.user_session,
            v.product_id,
            v.first_view
    ),

    valid_purchase AS (
        SELECT
            vc.user_session,
            vc.product_id,
            vc.first_view,
            vc.first_valid_cart,

            MIN(p.event_time) AS first_valid_purchase

        FROM valid_cart vc

        LEFT JOIN dec_events p
            ON vc.user_session = p.user_session
           AND vc.product_id = p.product_id
           AND p.event_type = 'purchase'
           AND p.event_time >= vc.first_valid_cart

        GROUP BY
            vc.user_session,
            vc.product_id,
            vc.first_view,
            vc.first_valid_cart
    )

    SELECT
        COUNT(*) AS view_count,

        COUNT(*) FILTER (
            WHERE first_valid_cart IS NOT NULL
        ) AS cart_count,

        COUNT(*) FILTER (
            WHERE first_valid_purchase IS NOT NULL
        ) AS purchase_count

    FROM valid_purchase
"""

result = con.sql(query).fetchone()

view_count = result[0]
cart_count = result[1]
purchase_count = result[2]



# 3. 전환율 계산

view_to_cart_rate = (
    cart_count / view_count * 100
)

cart_to_purchase_rate = (
    purchase_count / cart_count * 100
)

view_to_purchase_rate = (
    purchase_count / view_count * 100
)


# 4. 최종 결과 출력

print("\n===== 12월 최종 전환 퍼널 =====")

print(
    f"View                         : "
    f"{view_count:,}"
)

print(
    f"View → Cart                  : "
    f"{cart_count:,}"
)

print(
    f"View → Cart → Purchase       : "
    f"{purchase_count:,}"
)

print(
    f"View → Cart 전환율           : "
    f"{view_to_cart_rate:.2f}%"
)

print(
    f"Cart → Purchase 전환율       : "
    f"{cart_to_purchase_rate:.2f}%"
)

print(
    f"View → Purchase 최종 전환율  : "
    f"{view_to_purchase_rate:.2f}%"
)

# 5. 연결 종료

con.close()