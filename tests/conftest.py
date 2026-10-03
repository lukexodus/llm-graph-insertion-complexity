"""
conftest.py — Shared pytest fixtures for LLM graph-insertion complexity tests.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from graph_insertion.loader import DEFAULT_DATASET_ROOT


@pytest.fixture
def dataset_root() -> Path:
    """Fixture providing the path to EKG-Dataset root directory.

    Skips tests requiring dataset files if the repository was cloned without
    repositories/ or if dataset files are missing.
    """
    if (
        not DEFAULT_DATASET_ROOT.is_dir()
        or not (DEFAULT_DATASET_ROOT / "DSA_gold_standard_MEKG.txt").is_file()
    ):
        pytest.skip(
            f"Dataset not found at {DEFAULT_DATASET_ROOT}. "
            "Clone repository with dataset or ensure repositories/dataset/EKG-Dataset is populated."
        )
    return DEFAULT_DATASET_ROOT


@pytest.fixture
def require_dataset(dataset_root: Path) -> Path:
    """Explicit alias for dataset_root fixture."""
    return dataset_root
