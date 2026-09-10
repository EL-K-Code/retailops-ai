{{ config(tags=['silver']) }}

select
    store_id,
    item_id,
    wm_yr_wk,
    count(*) as duplicate_rows
from {{ ref('fact_prices_weekly') }}
group by store_id, item_id, wm_yr_wk
having duplicate_rows > 1
