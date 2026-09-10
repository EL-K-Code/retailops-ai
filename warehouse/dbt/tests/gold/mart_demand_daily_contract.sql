{{ config(tags=['gold']) }}

with contract as (
    select
        count(*) as row_count,
        countif(
            series_id is null
            or date is null
            or item_id is null
            or store_id is null
            or department is null
            or category is null
            or state is null
            or units_sold is null
            or price_available is null
            or is_weekend is null
            or snap_active is null
        ) as required_null_rows,
        countif(units_sold < 0) as negative_unit_rows,
        countif(snap_active not in (0, 1)) as invalid_snap_rows,
        countif(sell_price is not null and sell_price <= 0) as invalid_price_rows,
        countif(price_available != (sell_price is not null)) as price_flag_mismatch_rows,
        countif(
            estimated_sales_value is distinct from
            cast(units_sold as numeric) * sell_price
        ) as sales_value_mismatch_rows
    from {{ ref('mart_demand_daily') }}
)

select *
from contract
where
    row_count != 59181090
    or required_null_rows != 0
    or negative_unit_rows != 0
    or invalid_snap_rows != 0
    or invalid_price_rows != 0
    or price_flag_mismatch_rows != 0
    or sales_value_mismatch_rows != 0
