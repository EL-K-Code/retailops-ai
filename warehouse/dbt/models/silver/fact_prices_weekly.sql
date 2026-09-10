{{
    config(
        materialized='table',
        partition_by={
            "field": "week_start_date",
            "data_type": "date",
            "granularity": "day",
        },
        cluster_by=["store_id", "item_id"],
    )
}}

with week_lookup as (
    select
        wm_yr_wk,
        min(date) as week_start_date
    from {{ ref('dim_date') }}
    group by wm_yr_wk
)

select
    prices.store_id,
    prices.item_id,
    prices.wm_yr_wk,
    weeks.week_start_date,
    prices.sell_price
from {{ ref('stg_sell_prices') }} as prices
left join week_lookup as weeks
    using (wm_yr_wk)
