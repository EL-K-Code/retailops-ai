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

with train as (
    select
        series_id,
        date,
        item_id,
        store_id,
        department,
        category,
        state,
        units_sold,
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
        extract(year from date) as year
    from {{ ref('ml_demand_split') }}
    where dataset_split = 'train'
),

features as (
    select
        *,
        lag(units_sold, 1) over (
            partition by series_id order by date
        ) as lag_1,
        lag(units_sold, 7) over (
            partition by series_id order by date
        ) as lag_7,
        lag(units_sold, 14) over (
            partition by series_id order by date
        ) as lag_14,
        lag(units_sold, 28) over (
            partition by series_id order by date
        ) as lag_28,
        avg(units_sold) over (
            partition by series_id
            order by date
            rows between 7 preceding and 1 preceding
        ) as rolling_mean_7,
        avg(units_sold) over (
            partition by series_id
            order by date
            rows between 28 preceding and 1 preceding
        ) as rolling_mean_28,
        stddev_samp(units_sold) over (
            partition by series_id
            order by date
            rows between 28 preceding and 1 preceding
        ) as rolling_std_28,
        count(units_sold) over (
            partition by series_id
            order by date
            rows between 28 preceding and 1 preceding
        ) as history_count_28,
        lag(sell_price, 7) over (
            partition by series_id order by date
        ) as sell_price_7d_ago
    from train
)

select
    series_id,
    date,
    item_id,
    store_id,
    department,
    category,
    state,
    units_sold,
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
    lag_1,
    lag_7,
    lag_14,
    lag_28,
    rolling_mean_7,
    rolling_mean_28,
    rolling_std_28,
    date_sub(date, interval 1 day) as feature_history_end_date,
    dataset_split
from features
where history_count_28 = 28
