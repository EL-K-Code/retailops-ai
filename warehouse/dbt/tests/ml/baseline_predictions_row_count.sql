{{ config(tags=['ml', 'baseline']) }}

select
    count(*) as actual_rows
from {{ ref('ml_baseline_predictions') }}
having count(*) != 853720
