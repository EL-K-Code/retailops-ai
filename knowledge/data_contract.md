# RetailOps data contract

## Source
RetailOps AI uses the public M5 Forecasting dataset with daily item-store sales, weekly sell prices,
and calendar/event information.

## Warehouse layers
Raw source files land immutably in Google Cloud Storage, load into BigQuery RAW, and are transformed
with dbt through STAGING, SILVER, and GOLD marts. The ML layer defines chronological train,
validation, and test windows plus leakage-safe features and target-free future covariates.

## Forecast horizon
The primary horizon is 28 days. Train ends on 2016-03-27, validation covers 2016-03-28 through
2016-04-24, and test covers 2016-04-25 through 2016-05-22.

## Known limitation
The project must not invent future prices, promotions, calendar events, or demand. Forecast serving
is restricted to horizons for which future covariates are available in the prepared ML contract.
