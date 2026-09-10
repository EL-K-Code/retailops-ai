{{ config(tags=['ml', 'baseline']) }}

select *
from {{ ref('ml_baseline_predictions') }}
where
    date not between date('{{ var("demand_validation_start") }}')
        and date('{{ var("demand_validation_end") }}')
    or forecast_step not between 1 and {{ var("demand_forecast_horizon_days") }}
    or last_value_source_date > date('{{ var("demand_train_end") }}')
    or seasonal_7_source_date > date('{{ var("demand_train_end") }}')
    or seasonal_28_source_date > date('{{ var("demand_train_end") }}')
    or naive_last_prediction < 0
    or seasonal_naive_7_prediction < 0
    or seasonal_naive_28_prediction < 0
