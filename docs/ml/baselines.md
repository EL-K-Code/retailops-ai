# Demand forecasting baselines

V2.2 establishes simple leakage-safe forecasting baselines before any learned model is introduced.

## Why baselines come first

A more complex model is only useful if it improves on simple, reproducible references under the same temporal evaluation contract.

All V2.2 scores are computed on the validation window only:

```text
2016-03-28 -> 2016-04-24
```

The final test window remains untouched.

## Baselines

### Last value

The final training observation for each item-store series is repeated for all 28 forecast days.

### Seasonal naive, period 7

The final seven observed training days are repeated recursively across the 28-day horizon. This avoids reading actual validation labels through a direct validation `LAG(7)`.

### Seasonal naive, period 28

The final 28 observed training days are reused once across the 28-day validation horizon.

## Auditable prediction sources

`ml_baseline_predictions` stores the historical source date used for every prediction. dbt tests fail if any source date crosses the training boundary.

## Metrics

The baseline comparison reports MAE, RMSE, and unweighted bottom-level mean RMSSE. It is not the official M5 WRMSSE, which additionally applies hierarchy-level aggregation and sales-value weights.

## Models

```text
ml_demand_split
      |
      +--> ml_rmsse_scale
      |
      +--> ml_baseline_predictions
                |
                v
         ml_baseline_series_metrics
                |
                v
         ml_baseline_metrics
```

Expected validation prediction rows:

```text
30,490 series x 28 days = 853,720
```

Expected `ml_baseline_metrics` rows: 3.

## Run

After the V2.1 ML contract and GOLD marts are available:

```bash
python scripts/run_dbt_baselines.py
```

Inspect `retailops_ml.ml_baseline_metrics` for the resulting validation scores.

Computing RMSSE scales reads the historical training demand table, so cloud execution can scan a substantial amount of BigQuery data. Check the active billing/free-tier context before running it.

## Scope boundary

V2.2 introduces no fitted parameters, feature engineering, hyperparameter search, or test-set evaluation.
