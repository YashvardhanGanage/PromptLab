import pytest
from app.dataset_service import DatasetService, ensure_starter_dataset
from app.database import init_db

def test_starter_dataset_seeding():
    init_db()
    ensure_starter_dataset()
    datasets = DatasetService.list_datasets()
    assert len(datasets) >= 1

    starter = next((d for d in datasets if d["id"] == "starter-sentiment-dataset"), None)
    assert starter is not None
    assert starter["total_examples"] == 30
    assert starter["train_count"] == 20
    assert starter["test_count"] == 10

    train_exs = DatasetService.get_examples("starter-sentiment-dataset", split="train")
    assert len(train_exs) == 20

    test_exs = DatasetService.get_examples("starter-sentiment-dataset", split="test")
    assert len(test_exs) == 10

def test_dataset_upload_deduplication_and_splitting():
    raw_records = [
        {"input": "Great app", "expected_output": "positive"},
        {"input": "Terrible bug", "expected_output": "negative"},
        {"input": "Great app", "expected_output": "positive"}, # Duplicate
        {"input": "", "expected_output": "neutral"}, # Missing input
        {"input": "Just okay", "expected_output": ""}, # Missing output
        {"input": "Normal response", "expected_output": "neutral"},
        {"input": "Loved the speed", "expected_output": "positive"}
    ]

    new_ds = DatasetService.create_dataset_from_records(
        name="Custom Test Dataset",
        description="Testing deduplication",
        filename="custom.json",
        records=raw_records,
        input_col="input",
        expected_col="expected_output",
        train_ratio=0.75
    )

    assert new_ds is not None
    assert new_ds["total_examples"] == 4 # 7 minus 1 duplicate and 2 missing
    assert new_ds["train_count"] == 3
    assert new_ds["test_count"] == 1
