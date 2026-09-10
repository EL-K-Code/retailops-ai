{{
    config(
        materialized='table',
        partition_by={
            "field": "date",
            "data_type": "date",
            "granularity": "day",
        },
        cluster_by=["store_id", "item_id"],
    )
}}

with validation as (
    select
        series_id,
        item_id,
        store_id,
        date,
        units_sold as actual_units_sold,
        date_diff(
            date,
            date('{{ var("demand_validation_start") }}'),
            day
        ) + 1 as forecast_step
    from {{ ref('ml_demand_split') }}
    where dataset_split = 'validation'
),

targets as (
    select
        *,
        date('{{ var("demand_train_end") }}') as last_value_source_date,
        date('{{ var("demand_train_end") }}')
            + (mod(forecast_step - 1, 7) - 6) as seasonal_7_source_date,
        date - {{ var("demand_forecast_horizon_days") }} as seasonal_28_source_date
    from validation
),

recent_training_history as (
    select
        series_id,
        date,
        units_sold
    from {{ ref('ml_demand_split') }}
    where dataset_split = 'train'
        and date between
            date('{{ var("demand_train_end") }}')
                - ({{ var("demand_forecast_horizon_days") }} - 1)
            and date('{{ var("demand_train_end") }}')
)

select
    targets.series_id,
    targets.item_id,
    targets.store_id,
    targets.date,
    targets.forecast_step,
    targets.actual_units_sold,
    targets.last_value_source_date,
    targets.seasonal_7_source_date,
    targets.seasonal_28_source_date,
    cast(last_value.units_sold as float64) as naive_last_prediction,
    cast(seasonal_7.units_sold as float64) as seasonal_naive_7_prediction,
    cast(seasonal_28.units_sold as float64) as seasonal_naive_28_prediction
from targets
left join recent_training_history as last_value
    on targets.series_id = last_value.series_id
    and targets.last_value_source_date = last_value.date
left join recent_training_history as seasonal_7
    on targets.series_id = seasonal_7.series_id
    and targets.seasonal_7_source_date = seasonal_7.date
left join recent_training_history as seasonal_28
    on targets.series_id = seasonal_28.series_id
    and targets.seasonal_28_source_date = seasonal_28.date
