{{ config(tags=['ml', 'baseline']) }}

with metrics as (
    select *
    from {{ ref('ml_baseline_metrics') }}
),
row_count as (
    select count(*) as metric_count
    from metrics
)

select *
from metrics
where
    series_count != 30490
    or evaluated_observations != 853720
    or mae < 0
    or rmse < 0
    or mean_rmsse < 0

union all

select
    '__invalid_row_count__' as baseline,
    -1 as series_count,
    -1 as evaluated_observations,
    -1.0 as mae,
    -1.0 as rmse,
    -1.0 as mean_rmsse
from row_count
where metric_count != 3
