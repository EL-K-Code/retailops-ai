{{ config(materialized='table', cluster_by=['baseline']) }}

with predictions_long as (
    select
        series_id,
        'naive_last' as baseline,
        actual_units_sold,
        naive_last_prediction as prediction
    from {{ ref('ml_baseline_predictions') }}

    union all

    select
        series_id,
        'seasonal_naive_7' as baseline,
        actual_units_sold,
        seasonal_naive_7_prediction as prediction
    from {{ ref('ml_baseline_predictions') }}

    union all

    select
        series_id,
        'seasonal_naive_28' as baseline,
        actual_units_sold,
        seasonal_naive_28_prediction as prediction
    from {{ ref('ml_baseline_predictions') }}
),

errors as (
    select
        series_id,
        baseline,
        cast(actual_units_sold as float64) - prediction as error
    from predictions_long
),

aggregated as (
    select
        series_id,
        baseline,
        count(*) as forecast_days,
        avg(abs(error)) as mae,
        avg(pow(error, 2)) as mse,
        sqrt(avg(pow(error, 2))) as rmse
    from errors
    group by series_id, baseline
)

select
    aggregated.series_id,
    aggregated.baseline,
    aggregated.forecast_days,
    aggregated.mae,
    aggregated.mse,
    aggregated.rmse,
    scale.rmsse_scale,
    sqrt(
        safe_divide(
            aggregated.mse,
            scale.rmsse_scale
        )
    ) as rmsse
from aggregated
inner join {{ ref('ml_rmsse_scale') }} as scale
    using (series_id)
