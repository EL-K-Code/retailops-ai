{{ config(tags=['silver']) }}

with sales_orphans as (
    select count(*) as orphan_rows
    from {{ ref('fact_sales_daily') }} as fact
    left join {{ ref('dim_product') }} as product
        using (item_id)
    left join {{ ref('dim_store') }} as store
        using (store_id)
    left join {{ ref('dim_date') }} as calendar
        using (date)
    where
        product.item_id is null
        or store.store_id is null
        or calendar.date is null
),

price_orphans as (
    select count(*) as orphan_rows
    from {{ ref('fact_prices_weekly') }} as fact
    left join {{ ref('dim_product') }} as product
        using (item_id)
    left join {{ ref('dim_store') }} as store
        using (store_id)
    left join {{ ref('dim_date') }} as calendar
        on fact.week_start_date = calendar.date
    where
        product.item_id is null
        or store.store_id is null
        or calendar.date is null
)

select 'fact_sales_daily' as model_name, orphan_rows
from sales_orphans
where orphan_rows > 0

union all

select 'fact_prices_weekly' as model_name, orphan_rows
from price_orphans
where orphan_rows > 0
