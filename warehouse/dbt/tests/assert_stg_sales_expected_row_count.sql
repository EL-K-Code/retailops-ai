select
    count(*) as actual_rows
from {{ ref('stg_sales') }}
having actual_rows != 59181090
