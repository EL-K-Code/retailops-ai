{{
    config(
        materialized='table',
        partition_by={
            "field": "date",
            "data_type": "date",
            "granularity": "day",
        },
        cluster_by=["store_id", "item_id"],
    )
}}

with sales as (
    select
        series_id,
        item_id,
        store_id,
        date,
        day_key,
        units_sold
    from {{ ref('fact_sales_daily') }}
),

calendar as (
    select
        date,
        wm_yr_wk,
        is_weekend,
        event_name_1,
        event_type_1,
        event_name_2,
        event_type_2,
        snap_ca,
        snap_tx,
        snap_wi
    from {{ ref('dim_date') }}
),

products as (
    select
        item_id,
        dept_id,
        cat_id
    from {{ ref('dim_product') }}
),

stores as (
    select
        store_id,
        state_id
    from {{ ref('dim_store') }}
),

prices as (
    select
        store_id,
        item_id,
        wm_yr_wk,
        sell_price
    from {{ ref('fact_prices_weekly') }}
)

select
    sales.series_id,
    sales.date,
    sales.day_key,
    calendar.wm_yr_wk,
    sales.item_id,
    sales.store_id,
    products.dept_id as department,
    products.cat_id as category,
    stores.state_id as state,
    sales.units_sold,
    prices.sell_price,
    cast(sales.units_sold as numeric) * prices.sell_price as estimated_sales_value,
    prices.sell_price is not null as price_available,
    calendar.is_weekend,
    calendar.event_name_1,
    calendar.event_type_1,
    calendar.event_name_2,
    calendar.event_type_2,
    case stores.state_id
        when 'CA' then calendar.snap_ca
        when 'TX' then calendar.snap_tx
        when 'WI' then calendar.snap_wi
    end as snap_active
from sales
inner join calendar
    using (date)
inner join products
    using (item_id)
inner join stores
    using (store_id)
left join prices
    on sales.store_id = prices.store_id
    and sales.item_id = prices.item_id
    and calendar.wm_yr_wk = prices.wm_yr_wk
