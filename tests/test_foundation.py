"""Foundation smoke tests."""

import retailops_ai


def test_package_is_importable() -> None:
    """The project package should be importable from the src layout."""
    assert retailops_ai.__version__ == "0.1.0"
