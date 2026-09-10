{{ config(tags=['feature']) }}

with stats as (
    select
        count(*) as actual_rows,
        min(date) as min_date,
        max(date) as max_date,
        countif(dataset_split = 'validation') as validation_rows,
        countif(dataset_split = 'test') as test_rows
    from {{ ref('ml_forecast_covariates') }}
)

select
    *
from stats
where
    actual_rows != 1707440
    or validation_rows != 853720
    or test_rows != 853720
    or min_date != date('{{ var("demand_validation_start") }}')
    or max_date != date('{{ var("demand_test_end") }}')
