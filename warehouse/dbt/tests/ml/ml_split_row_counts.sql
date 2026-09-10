{{ config(tags=['ml']) }}

with actual as (
    select
        dataset_split,
        count(*) as actual_rows
    from {{ ref('ml_demand_split') }}
    group by dataset_split
),
expected as (
    select 'train' as dataset_split, 57473650 as expected_rows
    union all
    select 'validation', 853720
    union all
    select 'test', 853720
)

select
    expected.dataset_split,
    actual.actual_rows,
    expected.expected_rows
from expected
left join actual using (dataset_split)
where actual.actual_rows is null
    or actual.actual_rows != expected.expected_rows
