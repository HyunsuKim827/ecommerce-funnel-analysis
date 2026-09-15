import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

con = duckdb.connect(
    str(BASE_DIR / "ecommerce.duckdb")
)

con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")

print("\n===== 비교 기능 대상 세션 Baseline =====")

result = con.sql("""
    WITH session_behavior AS (
        SELECT
            user_session,
            COUNT(*) AS viewed_products
        FROM funnel_session_product
        GROUP BY user_session
    )

    SELECT
        COUNT(*) AS view_count,
        SUM(f.cart_flag) AS cart_count,
        SUM(f.purchase_flag) AS purchase_count

    FROM funnel_session_product f

    JOIN session_behavior s
        ON f.user_session = s.user_session

    WHERE s.viewed_products >= 2
""").fetchone()

view_count, cart_count, purchase_count = result

view_to_cart = cart_count / view_count * 100
view_to_purchase = purchase_count / view_count * 100
cart_to_purchase = purchase_count / cart_count * 100

print(f"View 수                : {view_count:,}")
print(f"Cart 수                : {cart_count:,}")
print(f"Purchase 수            : {purchase_count:,}")
print(f"View → Cart Baseline   : {view_to_cart:.2f}%")
print(f"View → Purchase Baseline : {view_to_purchase:.2f}%")
print(f"Cart → Purchase        : {cart_to_purchase:.2f}%")


print("\n===== A/B Test 개선 목표 시나리오 =====")

baseline_cart = 4.08
baseline_purchase = 1.73

uplifts = [5, 10, 15]

for uplift in uplifts:
    cart_target = baseline_cart * (1 + uplift / 100)
    purchase_target = baseline_purchase * (1 + uplift / 100)

    print(
        f"상대 {uplift:2}% 개선 | "
        f"V→C {baseline_cart:.2f}% → {cart_target:.2f}% | "
        f"V→P {baseline_purchase:.2f}% → {purchase_target:.2f}%"
    )

import math

print("\n===== A/B Test 필요 표본 수 =====")

# Baseline / Target
p1 = 0.0408
p2 = 0.0449

# 유의수준 5% 양측검정 → z = 1.96
z_alpha = 1.96

# 검정력 80% → z = 0.84
z_beta = 0.84

# 두 비율의 평균
p_bar = (p1 + p2) / 2

# 두 집단 비율 비교 표본 수 공식
n = (
    (
        z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
        +
        z_beta * math.sqrt(
            p1 * (1 - p1)
            +
            p2 * (1 - p2)
        )
    ) ** 2
    /
    (p2 - p1) ** 2
)

n_per_group = math.ceil(n)
total_n = n_per_group * 2

print(f"A군 필요 표본 수 : {n_per_group:,}")
print(f"B군 필요 표본 수 : {n_per_group:,}")
print(f"총 필요 표본 수   : {total_n:,}")


import math

print("\n===== 개선폭별 A/B Test 필요 표본 수 =====")

baseline = 0.0408

uplifts = [5, 10, 15]

z_alpha = 1.96   # 유의수준 5%, 양측검정
z_beta = 0.84    # 검정력 80%

for uplift in uplifts:

    target = baseline * (1 + uplift / 100)

    p1 = baseline
    p2 = target
    p_bar = (p1 + p2) / 2

    n = (
        (
            z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
            +
            z_beta * math.sqrt(
                p1 * (1 - p1)
                +
                p2 * (1 - p2)
            )
        ) ** 2
        /
        (p2 - p1) ** 2
    )

    n_per_group = math.ceil(n)

    print(
        f"상대 {uplift:2}% 개선 | "
        f"V→C {baseline*100:.2f}% → {target*100:.2f}% | "
        f"A/B 각 {n_per_group:,} | "
        f"총 {n_per_group*2:,}"
    )
    

import math
import matplotlib.pyplot as plt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

mde_labels = ['5%', '10%', '15%']
total_samples = [301956, 77248, 35112]

plt.figure(figsize=(8, 5))

plt.bar(
    mde_labels,
    total_samples
)

plt.xlabel('Relative improvement (MDE)')
plt.ylabel('Required total sample size')
plt.title('Required sample size by MDE')

for i, value in enumerate(total_samples):
    plt.text(
        i,
        value,
        f'{value:,}',
        ha='center',
        va='bottom'
    )

plt.tight_layout()

OUTPUT_PATH = BASE_DIR / "abtest_sample_size_by_mde.png"

plt.savefig(
    OUTPUT_PATH,
    dpi=200,
    bbox_inches='tight'
)

plt.show()

print(f"차트 저장 완료: {OUTPUT_PATH}")

con.close()