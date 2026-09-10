{{ config(tags=['gold']) }}

with store_duplicates as (
    select
        date,
        store_id,
        count(*) as duplicate_rows
    from {{ ref('mart_store_daily_sales') }}
    group by date, store_id
    having duplicate_rows > 1
),

product_duplicates as (
    select
        date,
        item_id,
        count(*) as duplicate_rows
    from {{ ref('mart_product_daily_sales') }}
    group by date, item_id
    having duplicate_rows > 1
)

select 'store' as mart_name, cast(date as string) as date_key, store_id as entity_id, duplicate_rows
from store_duplicates

union all

select 'product' as mart_name, cast(date as string) as date_key, item_id as entity_id, duplicate_rows
from product_duplicates
