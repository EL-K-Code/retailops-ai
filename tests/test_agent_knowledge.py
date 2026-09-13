from retailops_ai.agent.knowledge import LexicalKnowledgeRetriever, load_markdown_chunks


def test_lexical_retriever_returns_relevant_section(tmp_path):
    (tmp_path / "policy.md").write_text(
        "# Inventory\nDemand forecasts are not automatic reorder quantities.\n\n"
        "# Metrics\nRMSSE evaluates forecast error.",
        encoding="utf-8",
    )
    chunks = load_markdown_chunks(tmp_path)
    retriever = LexicalKnowledgeRetriever(chunks)

    hits = retriever.search("Should forecast demand trigger an automatic reorder?", top_k=2)

    assert hits
    assert hits[0].section == "Inventory"
    assert "reorder" in hits[0].text.lower()


def test_lexical_retriever_returns_empty_for_no_overlap(tmp_path):
    (tmp_path / "policy.md").write_text("# Inventory\nSafety stock policy.", encoding="utf-8")
    retriever = LexicalKnowledgeRetriever(load_markdown_chunks(tmp_path))

    assert retriever.search("astronomy telescope", top_k=3) == []
