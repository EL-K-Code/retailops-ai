from retailops_ai.workspace.scenarios import MemoryScenarioStore


def test_memory_scenario_store_is_owner_scoped_and_records_history() -> None:
    store = MemoryScenarioStore()
    alice = store.save(
        "alice@example.com",
        {
            "name": "CA replenishment",
            "item_id": "FOODS_1_001",
            "store_id": "CA_1",
            "split": "test",
            "current_stock": 20.0,
            "incoming_units": 10.0,
            "lead_time_days": 3,
            "safety_stock": 6.0,
            "economics": None,
        },
    )
    store.save(
        "bob@example.com",
        {
            "name": "Other workspace",
            "item_id": "FOODS_1_002",
            "store_id": "TX_1",
            "split": "test",
            "current_stock": 5.0,
            "incoming_units": 0.0,
            "lead_time_days": 0,
            "safety_stock": 2.0,
            "economics": None,
        },
    )

    assert len(store.list("alice@example.com")) == 1
    assert store.get("alice@example.com", alice["id"]) is not None
    assert store.get("bob@example.com", alice["id"]) is None

    event = store.record_run(
        "alice@example.com",
        alice,
        {
            "risk_level": "high",
            "projected_end_inventory": -3.0,
            "review_quantity": 9.0,
            "stockout_day": 5,
            "recommended_action": "review_reorder",
        },
    )

    assert event["scenario_id"] == alice["id"]
    assert store.history("alice@example.com")[0]["risk_level"] == "high"
    assert store.list("alice@example.com")[0]["latest_risk"] == "high"


def test_memory_scenario_store_deletes_only_owner_record() -> None:
    store = MemoryScenarioStore()
    saved = store.save(
        "owner",
        {
            "name": "Scenario",
            "item_id": "FOODS_1_001",
            "store_id": "CA_1",
            "split": "validation",
            "current_stock": 10.0,
            "incoming_units": 0.0,
            "lead_time_days": 0,
            "safety_stock": 0.0,
            "economics": None,
        },
    )

    assert store.delete("other", saved["id"]) is False
    assert store.delete("owner", saved["id"]) is True
    assert store.list("owner") == []
