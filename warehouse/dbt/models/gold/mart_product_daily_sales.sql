{{
    config(
        materialized='table',
        partition_by={
            "field": "date",
            "data_type": "date",
            "granularity": "day",
        },
        cluster_by=["item_id"],
    )
}}

select
    date,
    item_id,
    department,
    category,
    sum(units_sold) as total_units_sold,
    countif(units_sold > 0) as stores_with_sales,
    avg(sell_price) as average_sell_price,
    sum(estimated_sales_value) as estimated_sales_value,
    safe_divide(
        countif(price_available),
        count(*)
    ) as price_coverage_rate
from {{ ref('mart_demand_daily') }}
group by
    date,
    item_id,
    department,
    category
