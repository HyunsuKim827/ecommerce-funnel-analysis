import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(
    str(BASE_DIR / "ecommerce.duckdb")
)

con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")

print("\n===== 상위 카테고리별 가격대 구성 =====")

result = con.sql("""
    WITH top_categories AS (
        SELECT
            category_code
        FROM first_view_category
        WHERE category_code IS NOT NULL
        GROUP BY category_code
        ORDER BY COUNT(*) DESC
        LIMIT 10
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

        COUNT(*) AS view_count

    FROM first_view_category c

    JOIN first_view_price p
        ON c.user_session = p.user_session
       AND c.product_id = p.product_id

    JOIN top_categories t
        ON c.category_code = t.category_code

    GROUP BY
        c.category_code,
        price_group

    ORDER BY
        c.category_code,
        view_count DESC
""").fetchall()

for category, price_group, count in result:
    print(f"{category:35} | {price_group:8} | {count:,}")

print("\n===== construction.tools.light 가격대별 전환율 =====")

result = con.sql("""
    SELECT
        CASE
            WHEN p.view_price = 0 THEN '0_price'
            WHEN p.view_price <= 58.95 THEN 'Q1_low'
            WHEN p.view_price <= 153.47 THEN 'Q2'
            WHEN p.view_price <= 334.13 THEN 'Q3'
            ELSE 'Q4_high'
        END AS price_group,

        COUNT(*) AS view_count,
        AVG(f.cart_flag) * 100 AS view_to_cart_rate,

        CASE
            WHEN SUM(f.cart_flag) > 0
            THEN SUM(f.purchase_flag) * 100.0 / SUM(f.cart_flag)
        END AS cart_to_purchase_rate,

        AVG(f.purchase_flag) * 100 AS view_to_purchase_rate

    FROM first_view_category c

    JOIN first_view_price p
        ON c.user_session = p.user_session
       AND c.product_id = p.product_id

    JOIN funnel_session_product f
        ON c.user_session = f.user_session
       AND c.product_id = f.product_id

    WHERE c.category_code = 'construction.tools.light'

    GROUP BY price_group
    ORDER BY MIN(p.view_price)
""").fetchall()

for group, views, vc_rate, cp_rate, vp_rate in result:
    print(
        f"{group:8} | "
        f"View {views:,} | "
        f"V→C {vc_rate:.2f}% | "
        f"C→P {cp_rate:.2f}% | "
        f"V→P {vp_rate:.2f}%"
    )

print("\n===== sport.bicycle 가격대별 전환율 =====")

result = con.sql("""
    SELECT
        CASE
            WHEN p.view_price = 0 THEN '0_price'
            WHEN p.view_price <= 58.95 THEN 'Q1_low'
            WHEN p.view_price <= 153.47 THEN 'Q2'
            WHEN p.view_price <= 334.13 THEN 'Q3'
            ELSE 'Q4_high'
        END AS price_group,

        COUNT(*) AS view_count,
        AVG(f.cart_flag) * 100 AS view_to_cart_rate,

        CASE
            WHEN SUM(f.cart_flag) > 0
            THEN SUM(f.purchase_flag) * 100.0 / SUM(f.cart_flag)
        END AS cart_to_purchase_rate,

        AVG(f.purchase_flag) * 100 AS view_to_purchase_rate

    FROM first_view_category c

    JOIN first_view_price p
        ON c.user_session = p.user_session
       AND c.product_id = p.product_id

    JOIN funnel_session_product f
        ON c.user_session = f.user_session
       AND c.product_id = f.product_id

    WHERE c.category_code = 'sport.bicycle'

    GROUP BY price_group
    ORDER BY MIN(p.view_price)
""").fetchall()

for group, views, vc_rate, cp_rate, vp_rate in result:
    print(
        f"{group:8} | "
        f"View {views:,} | "
        f"V→C {vc_rate:.2f}% | "
        f"C→P {cp_rate:.2f}% | "
        f"V→P {vp_rate:.2f}%"
    )

print("\n===== 세션별 조회 상품 수 분포 =====")

session_stats = con.sql("""
    WITH session_behavior AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products
        FROM funnel_session_product
        GROUP BY user_session
    )

    SELECT
        COUNT(*) AS sessions,
        AVG(viewed_products) AS avg_products,
        MEDIAN(viewed_products) AS median_products,
        QUANTILE_CONT(viewed_products, 0.75) AS p75,
        QUANTILE_CONT(viewed_products, 0.90) AS p90,
        QUANTILE_CONT(viewed_products, 0.95) AS p95,
        QUANTILE_CONT(viewed_products, 0.99) AS p99,
        MAX(viewed_products) AS max_products
    FROM session_behavior
""").fetchone()

labels = [
    "세션 수", "평균", "중앙값", "75%",
    "90%", "95%", "99%", "최댓값"
]

for label, value in zip(labels, session_stats):
    if label == "세션 수":
        print(f"{label:6} : {int(value):,}")
    else:
        print(f"{label:6} : {value:.2f}")

print("\n===== 세션 조회 상품 수별 전환율 =====")

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
            f.*,
            s.viewed_products,

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
        COUNT(DISTINCT user_session) AS session_count,
        COUNT(*) AS view_count,
        AVG(cart_flag) * 100 AS view_to_cart_rate,

        CASE
            WHEN SUM(cart_flag) > 0
            THEN SUM(purchase_flag) * 100.0 / SUM(cart_flag)
        END AS cart_to_purchase_rate,

        AVG(purchase_flag) * 100 AS view_to_purchase_rate

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

for group, sessions, views, vc, cp, vp in result:
    print(
        f"{group:4} | "
        f"Session {sessions:,} | "
        f"View {views:,} | "
        f"V→C {vc:.2f}% | "
        f"C→P {cp:.2f}% | "
        f"V→P {vp:.2f}%"
    )

print("\n===== construction.tools.light 세션 탐색량별 전환율 =====")

result = con.sql("""
    WITH session_behavior AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products
        FROM funnel_session_product
        GROUP BY user_session
    )

    SELECT
        CASE
            WHEN s.viewed_products = 1 THEN '1'
            WHEN s.viewed_products <= 3 THEN '2-3'
            WHEN s.viewed_products <= 6 THEN '4-6'
            WHEN s.viewed_products <= 20 THEN '7-20'
            ELSE '21+'
        END AS session_group,

        COUNT(*) AS view_count,
        AVG(f.cart_flag) * 100 AS view_to_cart_rate,

        CASE
            WHEN SUM(f.cart_flag) > 0
            THEN SUM(f.purchase_flag) * 100.0 / SUM(f.cart_flag)
        END AS cart_to_purchase_rate,

        AVG(f.purchase_flag) * 100 AS view_to_purchase_rate

    FROM funnel_session_product f

    JOIN session_behavior s
        ON f.user_session = s.user_session

    JOIN first_view_category c
        ON f.user_session = c.user_session
       AND f.product_id = c.product_id

    WHERE c.category_code = 'construction.tools.light'

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

for group, views, vc, cp, vp in result:
    print(
        f"{group:4} | "
        f"View {views:,} | "
        f"V→C {vc:.2f}% | "
        f"C→P {cp:.2f}% | "
        f"V→P {vp:.2f}%"
    )