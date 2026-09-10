{{ config(tags=['silver']) }}

select 'dim_date' as model_name, count(*) as actual_rows, 1969 as expected_rows
from {{ ref('dim_date') }}
having count(*) != 1969

union all

select 'dim_product' as model_name, count(*) as actual_rows, 3049 as expected_rows
from {{ ref('dim_product') }}
having count(*) != 3049

union all

select 'dim_store' as model_name, count(*) as actual_rows, 10 as expected_rows
from {{ ref('dim_store') }}
having count(*) != 10
