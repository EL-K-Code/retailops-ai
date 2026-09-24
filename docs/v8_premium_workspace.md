# V8 Premium Workspace

V8 is a product-quality pass over RetailOps AI. The objective is to make the platform usable as an
operator workspace rather than presenting the user with a collection of technical demos.

## Product principles

The interface follows four principles:

1. **Task area first.** Navigation is visually quieter than the work surface.
2. **Operational density.** Prefer compact KPIs, time series, ranked lists and status signals over
   long explanatory paragraphs.
3. **Progressive disclosure.** Technical detail remains available in Model, Monitoring,
   Architecture and Knowledge pages instead of competing with the business workflow.
4. **No fake controls.** Top-bar actions navigate to working product surfaces.

These choices are inspired by modern enterprise product patterns such as Linear's reduced visual
noise and content hierarchy, and observability dashboards that combine query values, time series,
rankings and status widgets.

## Dashboard analytics

All V8 dashboard metrics are descriptive queries over the existing GOLD marts.

### Demand pulse

Daily total observed demand over the selected 28-day split.

### Demand variability

Coefficient of variation of the 28 daily total-demand observations:

~~~text
CV = standard deviation(daily units) / mean(daily units)
~~~

It is a descriptive stability signal, not a forecast-uncertainty metric.

### Category mix

Observed units grouped by M5 product category.

### Weekly rhythm

Average total demand by weekday within the selected split.

### Context indicators

- weekend unit share;
- SNAP-active unit share;
- event-day unit share;
- price coverage;
- average available sell price.

These are descriptive associations only. The UI must not present them as causal effects.

### Store contribution

Top stores by observed units, with estimated sales value and share of selected-window demand.

## Saved scenarios

Decision Lab scenarios can be saved with:

- scenario name;
- item and store;
- evaluation split;
- current stock;
- incoming PO;
- lead time;
- safety stock;
- optional economic assumptions.

When the agent service uses PostgreSQL checkpointing, the same Cloud SQL database also stores
scenario records and decision history. IAP-authenticated email identity is used as the owner key.
Local development falls back to an in-memory workspace store.

## Portfolio scan

The Scenario Workspace accepts a CSV with up to 25 rows.

Required columns:

~~~text
item_id,store_id,current_stock
~~~

Optional columns:

~~~text
name,split,incoming_units,lead_time_days,safety_stock
~~~

Example:

~~~csv
name,item_id,store_id,split,current_stock,incoming_units,lead_time_days,safety_stock
Base CA,FOODS_1_001,CA_1,test,20,10,3,6
Supplier delay,FOODS_1_001,CA_1,test,20,10,8,6
Low stock,FOODS_1_002,CA_1,test,5,0,0,3
~~~

The backend evaluates at most five scenarios concurrently to avoid turning a portfolio demo into an
unbounded fan-out against the private Forecast API.

## Decision history

Running a saved scenario records server-side decision metadata:

- scenario and entity;
- risk level;
- projected end inventory;
- stockout day;
- review quantity;
- recommended advisory action;
- timestamp.

This history is an audit aid. It does not represent execution in an ERP, OMS or replenishment
system.

## Cloud validation boundary

V8 code must pass CI before merge. The PostgreSQL persistence and new BigQuery dashboard queries are
only described as cloud-validated after the merged Cloud Run deployment and browser/API smoke tests
succeed.
