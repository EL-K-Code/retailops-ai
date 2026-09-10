{{ config(materialized='table') }}

with training as (
    select
        series_id,
        date,
        units_sold,
        min(if(units_sold > 0, date, null)) over (
            partition by series_id
        ) as first_nonzero_date
    from {{ ref('ml_demand_split') }}
    where dataset_split = 'train'
),

differences as (
    select
        series_id,
        date,
        first_nonzero_date,
        units_sold,
        lag(units_sold) over (
            partition by series_id
            order by date
        ) as previous_units_sold
    from training
)

select
    series_id,
    avg(
        pow(
            cast(units_sold - previous_units_sold as float64),
            2
        )
    ) as rmsse_scale,
    count(*) as scale_observations
from differences
where date > first_nonzero_date
group by series_id
