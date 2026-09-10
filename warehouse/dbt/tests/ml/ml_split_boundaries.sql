{{ config(tags=['ml']) }}

with actual as (
    select
        dataset_split,
        min(date) as min_date,
        max(date) as max_date
    from {{ ref('ml_demand_split') }}
    group by dataset_split
),
expected as (
    select 'train' as dataset_split, date('2011-01-29') as min_date, date('2016-03-27') as max_date
    union all
    select 'validation', date('2016-03-28'), date('2016-04-24')
    union all
    select 'test', date('2016-04-25'), date('2016-05-22')
)

select
    expected.dataset_split,
    actual.min_date as actual_min_date,
    actual.max_date as actual_max_date,
    expected.min_date as expected_min_date,
    expected.max_date as expected_max_date
from expected
left join actual using (dataset_split)
where actual.min_date is null
    or actual.min_date != expected.min_date
    or actual.max_date != expected.max_date
