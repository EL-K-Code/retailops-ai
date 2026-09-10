{{ config(materialized='view') }}

with covariates as (
    select
        series_id,
        date,
        item_id,
        store_id,
        department,
        category,
        state,
        sell_price,
        price_available,
        is_weekend,
        event_name_1,
        event_type_1,
        event_name_2,
        event_type_2,
        snap_active,
        dataset_split,
        extract(dayofweek from date) as day_of_week,
        extract(day from date) as day_of_month,
        extract(week from date) as week_of_year,
        extract(month from date) as month,
        extract(year from date) as year,
        lag(sell_price, 7) over (
            partition by series_id order by date
        ) as sell_price_7d_ago
    from {{ ref('ml_demand_split') }}
)

select
    series_id,
    date,
    item_id,
    store_id,
    department,
    category,
    state,
    sell_price,
    price_available,
    safe_divide(sell_price - sell_price_7d_ago, sell_price_7d_ago) as price_change_7d,
    is_weekend,
    event_name_1,
    event_type_1,
    event_name_2,
    event_type_2,
    snap_active,
    day_of_week,
    day_of_month,
    week_of_year,
    month,
    year,
    dataset_split
from covariates
where dataset_split in ('validation', 'test')
