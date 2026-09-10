{{ config(materialized='view') }}

select
    id as series_id,
    item_id,
    store_id,
    date,
    day_key,
    units_sold
from {{ ref('stg_sales') }}
