{{ config(tags=['feature']) }}

select
    count(*) as actual_rows
from {{ ref('ml_training_features') }}
having actual_rows != 56619930
