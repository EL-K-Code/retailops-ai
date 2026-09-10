{{ config(tags=['ml', 'baseline']) }}

select count(*) as actual_rows
from {{ ref('ml_rmsse_scale') }}
having count(*) != 30490
