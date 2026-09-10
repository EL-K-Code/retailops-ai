{{ config(tags=['feature']) }}

select
    *
from {{ ref('ml_training_features') }}
where
    dataset_split != 'train'
    or feature_history_end_date >= date
    or lag_1 is null
    or lag_7 is null
    or lag_14 is null
    or lag_28 is null
    or rolling_mean_7 is null
    or rolling_mean_28 is null
    or rolling_std_28 is null
