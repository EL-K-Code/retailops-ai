# Demand forecasting model card

## Model
The first learned forecasting model is a global LightGBM Poisson regressor. It predicts item-store
demand recursively across a 28-day horizon using lag and rolling-demand history plus target-free
future covariates.

## Validated local result
A real BigQuery-backed run trained on 2,744,100 rows using a 90-day lookback and 100 boosting rounds.
Validation results were MAE 1.076782, RMSE 2.175634, and mean bottom-level RMSSE 0.771130.

The strongest implemented baseline on mean RMSSE is naive_last at 0.952306. The learned model beat
all implemented baselines on the validation window.

## Metric limitation
The reported RMSSE is an unweighted mean across bottom-level item-store series. It is not the
official hierarchical M5 WRMSSE metric.

## Cloud validation status
The Vertex AI MLOps and Cloud Run serving code paths are implemented, but they must not be described
as cloud-validated until real GCP executions have completed successfully.
