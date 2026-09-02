import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(str(BASE_DIR / "ecommerce.duckdb"))

print("\n===== 결측치 및 가격 이상값 확인 =====")

query = f"""
    SELECT
        COUNT(*) AS total_rows,

        COUNT(*) - COUNT(category_code) AS null_category,
        ROUND(
            (COUNT(*) - COUNT(category_code)) * 100.0 / COUNT(*),
            2
        ) AS null_category_pct,

        COUNT(*) - COUNT(brand) AS null_brand,
        ROUND(
            (COUNT(*) - COUNT(brand)) * 100.0 / COUNT(*),
            2
        ) AS null_brand_pct,

        COUNT(*) - COUNT(price) AS null_price,

        COUNT(*) FILTER (WHERE price = 0) AS zero_price,
        COUNT(*) FILTER (WHERE price < 0) AS negative_price

    FROM dec_events
"""

print("\n===== 결측치 상세 확인 =====")

query = f"""
    SELECT 'category_code 결측' AS item,
           COUNT(*) - COUNT(category_code) AS count
    FROM dec_events

    UNION ALL

    SELECT 'brand 결측',
           COUNT(*) - COUNT(brand)
    FROM dec_events

    UNION ALL

    SELECT 'price 결측',
           COUNT(*) - COUNT(price)
    FROM dec_events

    UNION ALL

    SELECT 'price = 0',
           COUNT(*) FILTER (WHERE price = 0)
    FROM dec_events

    UNION ALL

    SELECT 'price < 0',
           COUNT(*) FILTER (WHERE price < 0)
    FROM dec_events
"""

print(con.sql(query))

print("\n===== user_session 결측 이벤트 확인 =====")

query = f"""
    SELECT
        event_type,
        COUNT(*) AS count
    FROM dec_events
    WHERE user_session IS NULL
    GROUP BY event_type
    ORDER BY count DESC
"""

print(con.sql(query))

print("\n===== 세션당 상품 수 확인 =====")

query = f"""
    WITH session_products AS (
        SELECT
            user_session,
            COUNT(DISTINCT product_id) AS product_count
        FROM dec_events
        WHERE user_session IS NOT NULL
        GROUP BY user_session
    )

    SELECT
        COUNT(*) AS total_sessions,
        ROUND(AVG(product_count), 2) AS avg_products_per_session,
        MEDIAN(product_count) AS median_products_per_session,
        MAX(product_count) AS max_products_per_session,

        COUNT(*) FILTER (WHERE product_count = 1) AS single_product_sessions,
        COUNT(*) FILTER (WHERE product_count > 1) AS multi_product_sessions,

        ROUND(
            COUNT(*) FILTER (WHERE product_count > 1) * 100.0 / COUNT(*),
            2
        ) AS multi_product_pct

    FROM session_products
"""

print(con.sql(query))

print("\n===== 세션당 상품 수 요약 =====")

query = f"""
    WITH session_products AS (
        SELECT
            user_session,
            COUNT(DISTINCT product_id) AS product_count
        FROM dec_events
        WHERE user_session IS NOT NULL
        GROUP BY user_session
    )

    SELECT
        ROUND(AVG(product_count), 2) AS avg_products,
        MEDIAN(product_count) AS median_products,
        MAX(product_count) AS max_products
    FROM session_products
"""

print(con.sql(query))

print("\n===== 이벤트 순서 확인 =====")

query = f"""
    WITH event_times AS (
        SELECT
            user_session,
            product_id,

            MIN(event_time) FILTER (
                WHERE event_type = 'view'
            ) AS first_view,

            MIN(event_time) FILTER (
                WHERE event_type = 'cart'
            ) AS first_cart,

            MIN(event_time) FILTER (
                WHERE event_type = 'purchase'
            ) AS first_purchase

        FROM dec_events
        WHERE user_session IS NOT NULL
        GROUP BY user_session, product_id
    )

    SELECT
        COUNT(*) FILTER (
            WHERE first_view IS NOT NULL
              AND first_cart IS NOT NULL
              AND first_view <= first_cart
        ) AS view_to_cart_ordered,

        COUNT(*) FILTER (
            WHERE first_view IS NOT NULL
              AND first_cart IS NOT NULL
              AND first_view > first_cart
        ) AS view_cart_reversed,

        COUNT(*) FILTER (
            WHERE first_cart IS NOT NULL
              AND first_purchase IS NOT NULL
              AND first_cart <= first_purchase
        ) AS cart_to_purchase_ordered,

        COUNT(*) FILTER (
            WHERE first_cart IS NOT NULL
              AND first_purchase IS NOT NULL
              AND first_cart > first_purchase
        ) AS cart_purchase_reversed

    FROM event_times
"""

result = con.sql(query).fetchone()

print("view_to_cart_ordered     :", result[0])
print("view_cart_reversed       :", result[1])
print("cart_to_purchase_ordered :", result[2])
print("cart_purchase_reversed   :", result[3])

con.close()