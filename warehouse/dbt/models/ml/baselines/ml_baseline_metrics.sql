{{ config(materialized='table') }}

select
    baseline,
    count(*) as series_count,
    sum(forecast_days) as evaluated_observations,
    avg(mae) as mae,
    sqrt(avg(mse)) as rmse,
    avg(rmsse) as mean_rmsse
from {{ ref('ml_baseline_series_metrics') }}
group by baseline
