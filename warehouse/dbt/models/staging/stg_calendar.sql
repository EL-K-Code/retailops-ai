{{ config(materialized='view') }}

select
    date,
    wm_yr_wk,
    weekday,
    wday,
    month,
    year,
    d as day_key,
    event_name_1,
    event_type_1,
    event_name_2,
    event_type_2,
    snap_CA as snap_ca,
    snap_TX as snap_tx,
    snap_WI as snap_wi
from {{ source('raw', 'raw_calendar') }}
