from retailops_ai.agent.checkpointing import CheckpointerConfig, open_checkpointer


def test_memory_checkpoint_handle() -> None:
    handle = open_checkpointer(CheckpointerConfig())
    assert handle.backend == "memory"
    assert not handle.durable
    handle.close()
