select
    *
from {{ ref('stg_sales') }}
where units_sold < 0
