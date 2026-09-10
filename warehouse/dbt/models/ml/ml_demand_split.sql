{{ config(materialized='view') }}

select
    series_id,
    date,
    day_key,
    wm_yr_wk,
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
    case
        when date between date('{{ var("demand_train_start") }}')
            and date('{{ var("demand_train_end") }}') then 'train'
        when date between date('{{ var("demand_validation_start") }}')
            and date('{{ var("demand_validation_end") }}') then 'validation'
        when date between date('{{ var("demand_test_start") }}')
            and date('{{ var("demand_test_end") }}') then 'test'
    end as dataset_split
from {{ ref('mart_demand_daily') }}
where date between date('{{ var("demand_train_start") }}')
    and date('{{ var("demand_test_end") }}')
