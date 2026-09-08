import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(
    str(BASE_DIR / "ecommerce.duckdb")
)

con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")

result = con.sql("""
    SELECT
        COUNT(*) AS view_count,
        SUM(cart_flag) AS cart_count,
        SUM(purchase_flag) AS purchase_count
    FROM funnel_session_product
""").fetchone()

view_count, cart_count, purchase_count = result

print("===== 기본 퍼널 =====")
print(f"View     : {view_count:,}")
print(f"Cart     : {cart_count:,}")
print(f"Purchase : {purchase_count:,}")

# 전환율
view_to_cart_rate = cart_count / view_count * 100
cart_to_purchase_rate = purchase_count / cart_count * 100
view_to_purchase_rate = purchase_count / view_count * 100

# 이탈률
view_to_cart_drop = 100 - view_to_cart_rate
cart_to_purchase_drop = 100 - cart_to_purchase_rate

print("\n===== 퍼널 전환율 / 이탈률 =====")
print(f"View → Cart 전환율       : {view_to_cart_rate:.2f}%")
print(f"View → Cart 이탈률       : {view_to_cart_drop:.2f}%")
print(f"Cart → Purchase 전환율   : {cart_to_purchase_rate:.2f}%")
print(f"Cart → Purchase 이탈률   : {cart_to_purchase_drop:.2f}%")
print(f"View → Purchase 최종 전환율 : {view_to_purchase_rate:.2f}%")

# 단계별 미전환 건수
view_no_cart = view_count - cart_count
cart_no_purchase = cart_count - purchase_count

print("\n===== 단계별 미전환 건수 =====")
print(f"View 이후 Cart 없음       : {view_no_cart:,}")
print(f"Cart 이후 Purchase 없음   : {cart_no_purchase:,}")

print("\n===== 상품별 가격 변화 확인 =====")

price_check = con.sql("""
    SELECT
        COUNT(*) AS total_products,
        SUM(
            CASE
                WHEN price_count > 1 THEN 1
                ELSE 0
            END
        ) AS changed_price_products
    FROM (
        SELECT
            product_id,
            COUNT(DISTINCT price) AS price_count
        FROM dec_events
        WHERE event_type = 'view'
        GROUP BY product_id
    )
""").fetchone()

total_products, changed_products = price_check

print(f"View가 있는 상품 수       : {total_products:,}")
print(f"가격이 2개 이상인 상품 수 : {changed_products:,}")
print(f"가격 변동 상품 비율        : {changed_products / total_products * 100:.2f}%")

print("\n===== 첫 View 가격 테이블 생성 =====")

con.execute("""
    CREATE OR REPLACE TABLE first_view_price AS

    SELECT
        user_session,
        product_id,
        first(event_time ORDER BY event_time) AS first_view,
        first(price ORDER BY event_time) AS view_price

    FROM dec_events

    WHERE event_type = 'view'
      AND user_session IS NOT NULL

    GROUP BY
        user_session,
        product_id
""")

result = con.sql("""
    SELECT
        COUNT(*) AS total,
        COUNT(view_price) AS price_available
    FROM first_view_price
""").fetchone()

print(f"전체 행 수       : {result[0]:,}")
print(f"가격 확인 가능 수 : {result[1]:,}")

print("\n===== 첫 View 가격 분포 =====")

price_stats = con.sql("""
    SELECT
        MIN(view_price) AS min_price,
        QUANTILE_CONT(view_price, 0.25) AS q1,
        MEDIAN(view_price) AS median,
        QUANTILE_CONT(view_price, 0.75) AS q3,
        QUANTILE_CONT(view_price, 0.90) AS p90,
        QUANTILE_CONT(view_price, 0.99) AS p99,
        MAX(view_price) AS max_price,
        AVG(view_price) AS avg_price
    FROM first_view_price
""").fetchone()

labels = [
    "최솟값", "25%", "중앙값", "75%",
    "90%", "99%", "최댓값", "평균"
]

for label, value in zip(labels, price_stats):
    print(f"{label:6} : {value:.2f}")

print("\n===== 가격 구간별 데이터 수 =====")

price_groups = con.sql("""
    SELECT
        CASE
            WHEN view_price = 0 THEN '0_price'
            WHEN view_price <= 58.95 THEN 'Q1_low'
            WHEN view_price <= 153.47 THEN 'Q2'
            WHEN view_price <= 334.13 THEN 'Q3'
            ELSE 'Q4_high'
        END AS price_group,

        COUNT(*) AS view_count

    FROM first_view_price

    GROUP BY price_group
    ORDER BY
        MIN(view_price)
""").fetchall()

for group, count in price_groups:
    print(f"{group:10} : {count:,}")

print("\n===== 가격 구간별 전환율 =====")

price_funnel = con.sql("""
    SELECT
        CASE
            WHEN p.view_price = 0 THEN '0_price'
            WHEN p.view_price <= 58.95 THEN 'Q1_low'
            WHEN p.view_price <= 153.47 THEN 'Q2'
            WHEN p.view_price <= 334.13 THEN 'Q3'
            ELSE 'Q4_high'
        END AS price_group,

        COUNT(*) AS view_count,
        SUM(f.cart_flag) AS cart_count,
        SUM(f.purchase_flag) AS purchase_count,

        AVG(f.cart_flag) * 100 AS view_to_cart_rate,

        CASE
            WHEN SUM(f.cart_flag) > 0
            THEN SUM(f.purchase_flag) * 100.0 / SUM(f.cart_flag)
        END AS cart_to_purchase_rate,

        AVG(f.purchase_flag) * 100 AS view_to_purchase_rate

    FROM first_view_price p

    JOIN funnel_session_product f
        ON p.user_session = f.user_session
       AND p.product_id = f.product_id

    GROUP BY price_group
    ORDER BY MIN(p.view_price)
""").fetchall()

for row in price_funnel:
    group, views, carts, purchases, vc_rate, cp_rate, vp_rate = row

    print(
        f"{group:10} | "
        f"View {views:,} | "
        f"Cart {int(carts):,} | "
        f"Purchase {int(purchases):,} | "
        f"V→C {vc_rate:.2f}% | "
        f"C→P {cp_rate:.2f}% | "
        f"V→P {vp_rate:.2f}%"
    )

print("\n===== 첫 View 카테고리 테이블 생성 =====")

con.execute("""
    CREATE OR REPLACE TABLE first_view_category AS

    SELECT
        user_session,
        product_id,
        first(category_code ORDER BY event_time) AS category_code

    FROM dec_events

    WHERE event_type = 'view'
      AND user_session IS NOT NULL

    GROUP BY
        user_session,
        product_id
""")

result = con.sql("""
    SELECT
        COUNT(*) AS total,
        COUNT(category_code) AS category_available
    FROM first_view_category
""").fetchone()

print(f"전체 행 수          : {result[0]:,}")
print(f"카테고리 확인 가능 수 : {result[1]:,}")
print(f"카테고리 결측 수      : {result[0] - result[1]:,}")

print("\n===== View 상위 15개 카테고리 전환율 =====")

category_funnel = con.sql("""
    SELECT
        c.category_code,
        COUNT(*) AS view_count,
        SUM(f.cart_flag) AS cart_count,
        SUM(f.purchase_flag) AS purchase_count,
        AVG(f.cart_flag) * 100 AS view_to_cart_rate,

        CASE
            WHEN SUM(f.cart_flag) > 0
            THEN SUM(f.purchase_flag) * 100.0 / SUM(f.cart_flag)
        END AS cart_to_purchase_rate,

        AVG(f.purchase_flag) * 100 AS view_to_purchase_rate

    FROM first_view_category c

    JOIN funnel_session_product f
        ON c.user_session = f.user_session
       AND c.product_id = f.product_id

    WHERE c.category_code IS NOT NULL

    GROUP BY c.category_code
    ORDER BY view_count DESC
    LIMIT 15
""").fetchall()

for row in category_funnel:
    category, views, carts, purchases, vc_rate, cp_rate, vp_rate = row

    print(
        f"{category:35} | "
        f"View {views:,} | "
        f"V→C {vc_rate:.2f}% | "
        f"C→P {cp_rate:.2f}% | "
        f"V→P {vp_rate:.2f}%"
    )

print("\n===== 첫 View 브랜드 테이블 생성 =====")

con.execute("""
    CREATE OR REPLACE TABLE first_view_brand AS

    SELECT
        user_session,
        product_id,
        first(brand ORDER BY event_time) AS brand

    FROM dec_events

    WHERE event_type = 'view'
      AND user_session IS NOT NULL

    GROUP BY
        user_session,
        product_id
""")

result = con.sql("""
    SELECT
        COUNT(*) AS total,
        COUNT(brand) AS brand_available
    FROM first_view_brand
""").fetchone()

print(f"전체 행 수        : {result[0]:,}")
print(f"브랜드 확인 가능 수 : {result[1]:,}")
print(f"브랜드 결측 수      : {result[0] - result[1]:,}")

print("\n===== View 상위 15개 브랜드 전환율 =====")

brand_funnel = con.sql("""
    SELECT
        b.brand,
        COUNT(*) AS view_count,
        SUM(f.cart_flag) AS cart_count,
        SUM(f.purchase_flag) AS purchase_count,

        AVG(f.cart_flag) * 100 AS view_to_cart_rate,

        CASE
            WHEN SUM(f.cart_flag) > 0
            THEN SUM(f.purchase_flag) * 100.0 / SUM(f.cart_flag)
        END AS cart_to_purchase_rate,

        AVG(f.purchase_flag) * 100 AS view_to_purchase_rate

    FROM first_view_brand b

    JOIN funnel_session_product f
        ON b.user_session = f.user_session
       AND b.product_id = f.product_id

    WHERE b.brand IS NOT NULL

    GROUP BY b.brand
    ORDER BY view_count DESC
    LIMIT 15
""").fetchall()

for row in brand_funnel:
    brand, views, carts, purchases, vc_rate, cp_rate, vp_rate = row

    print(
        f"{brand:20} | "
        f"View {views:,} | "
        f"V→C {vc_rate:.2f}% | "
        f"C→P {cp_rate:.2f}% | "
        f"V→P {vp_rate:.2f}%"
    )

con.close()