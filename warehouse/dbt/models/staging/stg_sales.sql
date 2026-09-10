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

with unpivoted as (
    select
        id,
        item_id,
        dept_id,
        cat_id,
        store_id,
        state_id,
        day_key,
        units_sold
    from {{ source('raw', 'raw_sales') }}
    unpivot (
        units_sold for day_key in (
            {% for day in range(1, 1942) -%}
            d_{{ day }}{% if not loop.last %},{% endif %}
            {% endfor -%}
        )
    )
),

calendar as (
    select
        day_key,
        date
    from {{ ref('stg_calendar') }}
)

select
    unpivoted.id,
    unpivoted.item_id,
    unpivoted.dept_id,
    unpivoted.cat_id,
    unpivoted.store_id,
    unpivoted.state_id,
    unpivoted.day_key,
    calendar.date,
    unpivoted.units_sold
from unpivoted
inner join calendar using (day_key)
