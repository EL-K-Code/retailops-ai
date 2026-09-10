select
    *
from {{ ref('stg_sell_prices') }}
where sell_price <= 0
