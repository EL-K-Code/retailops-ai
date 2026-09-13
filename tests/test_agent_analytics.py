from retailops_ai.agent import analytics


CONFIG = analytics.AnalyticsConfig(
    project="retailops-ai-2026",
    location="us-central1",
    dbt_dataset="retailops",
)


def test_top_products_uses_allowlisted_gold_mart_and_parameterized_limit():
    spec = analytics.build_query_spec(
        analytics.AnalyticsRequest(operation="top_products", split="test", top_n=7),
        CONFIG,
    )

    assert "retailops_gold.mart_product_daily_sales" in spec.sql
    assert "limit @top_n" in spec.sql.lower()
    assert ("top_n", "INT64", 7) in spec.parameters


def test_baseline_metrics_uses_ml_contract_table_without_free_sql():
    spec = analytics.build_query_spec(
        analytics.AnalyticsRequest(operation="baseline_metrics", split="validation"),
        CONFIG,
    )

    assert "retailops_ml.ml_baseline_metrics" in spec.sql
    assert spec.parameters == []
