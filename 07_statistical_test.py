import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(
    str(BASE_DIR / "ecommerce.duckdb")
)

con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")

print("DuckDB 연결 완료")

print("\n===== 세션 탐색량 × Cart 전환 교차표 =====")

result = con.sql("""
    WITH session_behavior AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products
        FROM funnel_session_product
        GROUP BY user_session
    ),

    segmented AS (
        SELECT
            f.user_session,
            f.cart_flag,

            CASE
                WHEN s.viewed_products = 1 THEN '1'
                WHEN s.viewed_products <= 3 THEN '2-3'
                WHEN s.viewed_products <= 6 THEN '4-6'
                WHEN s.viewed_products <= 20 THEN '7-20'
                ELSE '21+'
            END AS session_group

        FROM funnel_session_product f

        JOIN session_behavior s
            ON f.user_session = s.user_session
    )

    SELECT
        session_group,

        SUM(CASE WHEN cart_flag = 1 THEN 1 ELSE 0 END) AS cart_yes,
        SUM(CASE WHEN cart_flag = 0 THEN 1 ELSE 0 END) AS cart_no

    FROM segmented

    GROUP BY session_group

    ORDER BY
        CASE session_group
            WHEN '1' THEN 1
            WHEN '2-3' THEN 2
            WHEN '4-6' THEN 3
            WHEN '7-20' THEN 4
            WHEN '21+' THEN 5
        END
""").fetchall()

for group, cart_yes, cart_no in result:
    print(
        f"{group:4} | "
        f"Cart O {cart_yes:,} | "
        f"Cart X {cart_no:,}"
    )
import math

print("\n===== 세션 탐색량 × Cart 전환 교차표 =====")

result = con.sql("""
    WITH session_behavior AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products
        FROM funnel_session_product
        GROUP BY user_session
    ),

    segmented AS (
        SELECT
            f.user_session,
            f.cart_flag,

            CASE
                WHEN s.viewed_products = 1 THEN '1'
                WHEN s.viewed_products <= 3 THEN '2-3'
                WHEN s.viewed_products <= 6 THEN '4-6'
                WHEN s.viewed_products <= 20 THEN '7-20'
                ELSE '21+'
            END AS session_group

        FROM funnel_session_product f

        JOIN session_behavior s
            ON f.user_session = s.user_session
    )

    SELECT
        session_group,
        SUM(CASE WHEN cart_flag = 1 THEN 1 ELSE 0 END) AS cart_yes,
        SUM(CASE WHEN cart_flag = 0 THEN 1 ELSE 0 END) AS cart_no

    FROM segmented

    GROUP BY session_group

    ORDER BY
        CASE session_group
            WHEN '1' THEN 1
            WHEN '2-3' THEN 2
            WHEN '4-6' THEN 3
            WHEN '7-20' THEN 4
            WHEN '21+' THEN 5
        END
""").fetchall()

for group, cart_yes, cart_no in result:
    print(
        f"{group:4} | "
        f"Cart O {cart_yes:,} | "
        f"Cart X {cart_no:,}"
    )


print("\n===== 카이제곱 검정 + Cramér's V =====")

observed = [
    [cart_yes, cart_no]
    for _, cart_yes, cart_no in result
]

row_totals = [sum(row) for row in observed]

col_totals = [
    sum(row[col] for row in observed)
    for col in range(2)
]

n = sum(row_totals)

chi2 = 0

for i in range(len(observed)):
    for j in range(2):

        expected = (
            row_totals[i]
            * col_totals[j]
            / n
        )

        chi2 += (
            (observed[i][j] - expected) ** 2
            / expected
        )

dof = (len(observed) - 1) * (2 - 1)

# 자유도 4일 때의 survival function
p_value = math.exp(-chi2 / 2) * (1 + chi2 / 2)

cramers_v = math.sqrt(
    chi2
    / (
        n
        * min(
            len(observed) - 1,
            2 - 1
        )
    )
)

print(f"Chi-square : {chi2:,.2f}")
print(f"자유도      : {dof}")
print(f"p-value    : {p_value:.6g}")
print(f"Cramér's V : {cramers_v:.4f}")

print("\n===== 세션 단위 탐색량 × Cart 발생 교차표 =====")

session_result = con.sql("""
    WITH session_summary AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products,
            MAX(cart_flag) AS any_cart
        FROM funnel_session_product
        GROUP BY user_session
    )

    SELECT
        CASE
            WHEN viewed_products = 1 THEN '1'
            WHEN viewed_products <= 3 THEN '2-3'
            WHEN viewed_products <= 6 THEN '4-6'
            WHEN viewed_products <= 20 THEN '7-20'
            ELSE '21+'
        END AS session_group,

        SUM(CASE WHEN any_cart = 1 THEN 1 ELSE 0 END) AS cart_yes,
        SUM(CASE WHEN any_cart = 0 THEN 1 ELSE 0 END) AS cart_no

    FROM session_summary

    GROUP BY session_group

    ORDER BY
        CASE session_group
            WHEN '1' THEN 1
            WHEN '2-3' THEN 2
            WHEN '4-6' THEN 3
            WHEN '7-20' THEN 4
            WHEN '21+' THEN 5
        END
""").fetchall()

for group, cart_yes, cart_no in session_result:
    total = cart_yes + cart_no
    rate = cart_yes / total * 100

    print(
        f"{group:4} | "
        f"Cart O {cart_yes:,} | "
        f"Cart X {cart_no:,} | "
        f"Cart 발생률 {rate:.2f}%"
    )

print("\n===== 세션 탐색량별 상품 Cart 전환 비율 =====")

result = con.sql("""
    WITH session_summary AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products,
            SUM(cart_flag) AS carted_products,
            SUM(cart_flag) * 1.0 / COUNT(*) AS cart_rate
        FROM funnel_session_product
        GROUP BY user_session
    )

    SELECT
        CASE
            WHEN viewed_products = 1 THEN '1'
            WHEN viewed_products <= 3 THEN '2-3'
            WHEN viewed_products <= 6 THEN '4-6'
            WHEN viewed_products <= 20 THEN '7-20'
            ELSE '21+'
        END AS session_group,

        COUNT(*) AS session_count,
        AVG(cart_rate) * 100 AS avg_cart_rate,
        MEDIAN(cart_rate) * 100 AS median_cart_rate

    FROM session_summary

    GROUP BY session_group

    ORDER BY
        CASE session_group
            WHEN '1' THEN 1
            WHEN '2-3' THEN 2
            WHEN '4-6' THEN 3
            WHEN '7-20' THEN 4
            WHEN '21+' THEN 5
        END
""").fetchall()

for group, sessions, avg_rate, median_rate in result:
    print(
        f"{group:4} | "
        f"Session {sessions:,} | "
        f"평균 Cart 비율 {avg_rate:.2f}% | "
        f"중앙값 {median_rate:.2f}%"
    )

print("\n===== 세션 탐색량별 상품 구매 전환 비율 =====")

result = con.sql("""
    WITH session_summary AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products,
            SUM(purchase_flag) AS purchased_products,
            SUM(purchase_flag) * 1.0 / COUNT(*) AS purchase_rate
        FROM funnel_session_product
        GROUP BY user_session
    )

    SELECT
        CASE
            WHEN viewed_products = 1 THEN '1'
            WHEN viewed_products <= 3 THEN '2-3'
            WHEN viewed_products <= 6 THEN '4-6'
            WHEN viewed_products <= 20 THEN '7-20'
            ELSE '21+'
        END AS session_group,

        COUNT(*) AS session_count,
        AVG(purchase_rate) * 100 AS avg_purchase_rate

    FROM session_summary

    GROUP BY session_group

    ORDER BY
        CASE session_group
            WHEN '1' THEN 1
            WHEN '2-3' THEN 2
            WHEN '4-6' THEN 3
            WHEN '7-20' THEN 4
            WHEN '21+' THEN 5
        END
""").fetchall()

for group, sessions, rate in result:
    print(
        f"{group:4} | "
        f"Session {sessions:,} | "
        f"평균 구매 전환 비율 {rate:.2f}%"
    )

print("\n===== 상위 5개 카테고리 가격대별 View→Cart 전환율 =====")

result = con.sql("""
    WITH top_categories AS (
        SELECT
            category_code
        FROM first_view_category
        WHERE category_code IS NOT NULL
        GROUP BY category_code
        ORDER BY COUNT(*) DESC
        LIMIT 5
    )

    SELECT
        c.category_code,

        CASE
            WHEN p.view_price = 0 THEN '0_price'
            WHEN p.view_price <= 58.95 THEN 'Q1_low'
            WHEN p.view_price <= 153.47 THEN 'Q2'
            WHEN p.view_price <= 334.13 THEN 'Q3'
            ELSE 'Q4_high'
        END AS price_group,

        COUNT(*) AS view_count,
        AVG(f.cart_flag) * 100 AS view_to_cart_rate

    FROM first_view_category c

    JOIN first_view_price p
        ON c.user_session = p.user_session
       AND c.product_id = p.product_id

    JOIN funnel_session_product f
        ON c.user_session = f.user_session
       AND c.product_id = f.product_id

    JOIN top_categories t
        ON c.category_code = t.category_code

    WHERE p.view_price > 0

    GROUP BY
        c.category_code,
        price_group

    ORDER BY
        c.category_code,
        CASE price_group
            WHEN 'Q1_low' THEN 1
            WHEN 'Q2' THEN 2
            WHEN 'Q3' THEN 3
            WHEN 'Q4_high' THEN 4
            ELSE 5
        END
""").fetchall()

for category, price_group, views, rate in result:
    print(
        f"{category:35} | "
        f"{price_group:8} | "
        f"View {views:,} | "
        f"V→C {rate:.2f}%"
    )