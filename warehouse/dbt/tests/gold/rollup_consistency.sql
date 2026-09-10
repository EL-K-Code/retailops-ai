{{ config(tags=['gold']) }}

with demand_by_date as (
    select
        date,
        sum(units_sold) as total_units_sold,
        sum(estimated_sales_value) as estimated_sales_value
    from {{ ref('mart_demand_daily') }}
    group by date
),

store_by_date as (
    select
        date,
        sum(total_units_sold) as total_units_sold,
        sum(estimated_sales_value) as estimated_sales_value
    from {{ ref('mart_store_daily_sales') }}
    group by date
),

product_by_date as (
    select
        date,
        sum(total_units_sold) as total_units_sold,
        sum(estimated_sales_value) as estimated_sales_value
    from {{ ref('mart_product_daily_sales') }}
    group by date
)

select
    demand.date,
    demand.total_units_sold as demand_units,
    stores.total_units_sold as store_units,
    products.total_units_sold as product_units,
    demand.estimated_sales_value as demand_value,
    stores.estimated_sales_value as store_value,
    products.estimated_sales_value as product_value
from demand_by_date as demand
inner join store_by_date as stores
    using (date)
inner join product_by_date as products
    using (date)
where
    demand.total_units_sold != stores.total_units_sold
    or demand.total_units_sold != products.total_units_sold
    or demand.estimated_sales_value is distinct from stores.estimated_sales_value
    or demand.estimated_sales_value is distinct from products.estimated_sales_value
