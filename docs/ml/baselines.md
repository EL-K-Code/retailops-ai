# Demand forecasting baselines

V2.2 establishes simple leakage-safe forecasting baselines before any learned model is introduced.

## Why baselines come first

A more complex model is only useful if it improves on simple, reproducible references under the same temporal evaluation contract.

All V2.2 scores are computed on the **validation window only**:

```text
2016-03-28 -> 2016-04-24
```

The final test window remains untouched.

## Baselines

### Last value

The final training observation for each item-store series is repeated for all 28 forecast days.

```text
y_hat(T + h) = y(T)
```

### Seasonal naive, period 7

The final seven observed training days are repeated recursively across the 28-day horizon.

This is intentionally different from blindly applying `LAG(7)` to validation rows. For horizons greater than seven days, a direct validation `LAG(7)` would read actual validation labels and create leakage.

### Seasonal naive, period 28

The final 28 observed training days are reused once across the 28-day validation horizon.

For each validation date `t`:

```text
y_hat(t) = y(t - 28 days)
```

Every source observation therefore lies inside the training window.

## Auditable prediction sources

`ml_baseline_predictions` stores the historical source date used for every prediction:

```text
last_value_source_date
seasonal_7_source_date
seasonal_28_source_date
```

dbt tests fail if any source date crosses the training boundary.

## Metrics

The baseline comparison reports:

- `MAE`;
- `RMSE`;
- `mean_rmsse`.

`mean_rmsse` is the unweighted mean of bottom-level item-store RMSSE values. It is **not** the official M5 WRMSSE, which additionally applies hierarchy-level aggregation and sales-value weights.

The RMSSE denominator is computed from the training series after its first non-zero demand observation, following the M5 scaling convention.

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

Expected `ml_baseline_metrics` rows:

```text
3
```

one for each baseline.

## Run

After the V2.1 ML contract and GOLD marts are available:

```bash
chmod +x scripts/run_dbt_baselines.sh
./scripts/run_dbt_baselines.sh
```

Inspect:

```text
retailops_ml.ml_baseline_metrics
```

for the resulting validation scores.

Computing RMSSE scales reads the historical training demand table, so cloud execution can scan a substantial amount of BigQuery data. Check the active billing/free-tier context before running it.

## Scope boundary

V2.2 introduces no fitted parameters, feature engineering, hyperparameter search, or test-set evaluation.

The next milestone can introduce leakage-safe lag/rolling features and a global learned model, using these baseline scores as the minimum performance bar.
