from retailops_ai.agent import analytics  # noqa: I001


CONFIG = analytics.AnalyticsConfig(
    project="retailops-ai-2026",
    location="us-central1",
    dbt_dataset="retailops",
)


def test_demand_anomaly_query_is_allowlisted_and_historical() -> None:
    spec = analytics.build_query_spec(
        analytics.AnalyticsRequest(operation="demand_anomalies", split="test", top_n=8),
        CONFIG,
    )

    assert "mart_demand_daily" in spec.sql
    assert "rows between 28 preceding and 1 preceding" in spec.sql
    assert "abs(anomaly_z) >= 3" in spec.sql


def test_daily_demand_query_supports_entity_filters() -> None:
    spec = analytics.build_query_spec(
        analytics.AnalyticsRequest(
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


def test_daily_trend_uses_gold_mart_and_orders_by_date() -> None:
    spec = analytics.build_query_spec(
        analytics.AnalyticsRequest(operation="daily_trend", split="test"),
        CONFIG,
    )

    assert "mart_demand_daily" in spec.sql
    assert "active_series" in spec.sql
    assert "order by date" in spec.sql.lower()


def test_category_summary_is_bounded_and_context_is_descriptive() -> None:
    category = analytics.build_query_spec(
        analytics.AnalyticsRequest(operation="category_summary", split="test", top_n=6),
        CONFIG,
    )
    context = analytics.build_query_spec(
        analytics.AnalyticsRequest(operation="demand_context", split="test"),
        CONFIG,
    )

    assert "group by category" in category.sql.lower()
    assert ("top_n", "INT64", 6) in category.parameters
    assert "weekend_unit_share" in context.sql
    assert "snap_active_unit_share" in context.sql
    assert "price_coverage_rate" in context.sql


def test_weekday_profile_is_calendar_ordered() -> None:
    spec = analytics.build_query_spec(
        analytics.AnalyticsRequest(operation="weekday_profile", split="validation"),
        CONFIG,
    )

    assert "extract(dayofweek from date)" in spec.sql.lower()
    assert "average_daily_units" in spec.sql
    assert "order by day_order" in spec.sql.lower()
