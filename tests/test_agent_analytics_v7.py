from retailops_ai.agent.analytics import AnalyticsConfig, build_query_spec
from retailops_ai.agent.schemas import AnalyticsRequest


CONFIG = AnalyticsConfig(
    project="retailops-ai-2026",
    location="us-central1",
    dbt_dataset="retailops",
)


def test_demand_anomaly_query_is_allowlisted_and_historical() -> None:
    spec = build_query_spec(
        AnalyticsRequest(operation="demand_anomalies", split="test", top_n=8),
        CONFIG,
    )

    assert "mart_demand_daily" in spec.sql
    assert "rows between 28 preceding and 1 preceding" in spec.sql
    assert "abs(anomaly_z) >= 3" in spec.sql


def test_daily_demand_query_supports_entity_filters() -> None:
    spec = build_query_spec(
        AnalyticsRequest(
            operation="daily_demand",
            split="validation",
            item_id="FOODS_1_001",
            store_id="CA_1",
        ),
        CONFIG,
    )

    assert "sum(units_sold) as daily_units" in spec.sql
    assert "@item_id" in spec.sql
    assert "@store_id" in spec.sql
