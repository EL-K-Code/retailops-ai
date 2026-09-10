select
    *
from {{ ref('stg_sales') }}
where
    id is null
    or item_id is null
    or store_id is null
    or day_key is null
    or date is null
    or units_sold is null
