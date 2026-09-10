{{ config(tags=['gold']) }}

select
    'store' as mart_name,
    cast(date as string) as date_key,
    store_id as entity_id,
    price_coverage_rate
from {{ ref('mart_store_daily_sales') }}
where
    total_units_sold < 0
    or active_item_count < 0
    or price_coverage_rate < 0
    or price_coverage_rate > 1

union all

select
    'product' as mart_name,
    cast(date as string) as date_key,
    item_id as entity_id,
    price_coverage_rate
from {{ ref('mart_product_daily_sales') }}
where
    total_units_sold < 0
    or stores_with_sales < 0
    or price_coverage_rate < 0
    or price_coverage_rate > 1
