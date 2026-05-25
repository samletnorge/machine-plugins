"""Tests for Dataset management."""

import pytest
import json
import csv
from pathlib import Path
from eval_support.dataset import Dataset, EvalSample


def test_eval_sample_minimal():
    sample = EvalSample(input="What is Python?")
    assert sample.input == "What is Python?"
    assert sample.expected_output is None
    assert sample.context is None
    assert sample.tags == []


def test_eval_sample_full():
    sample = EvalSample(
        input="What is Python?",
        expected_output="A programming language",
        context={"documents": ["Python is..."]},
        tags=["basic", "python"],
    )
    assert sample.expected_output == "A programming language"
    assert sample.tags == ["basic", "python"]


def test_dataset_create_from_list():
    samples = [
        EvalSample(input="Q1", expected_output="A1"),
        EvalSample(input="Q2", expected_output="A2"),
    ]
    ds = Dataset(name="test", samples=samples)
    assert ds.name == "test"
    assert len(ds) == 2


def test_dataset_iteration():
    samples = [EvalSample(input=f"Q{i}") for i in range(5)]
    ds = Dataset(name="iter_test", samples=samples)
    collected = list(ds)
    assert len(collected) == 5


def test_dataset_filter_by_tag():
    samples = [
        EvalSample(input="Q1", tags=["easy"]),
        EvalSample(input="Q2", tags=["hard"]),
        EvalSample(input="Q3", tags=["easy", "python"]),
    ]
    ds = Dataset(name="tagged", samples=samples)
    easy = ds.filter(tags=["easy"])
    assert len(easy) == 2
    assert easy.name == "tagged[easy]"


def test_dataset_load_from_json(tmp_path: Path):
    data = [
        {"input": "Q1", "expected_output": "A1"},
        {"input": "Q2", "expected_output": "A2", "tags": ["test"]},
    ]
    path = tmp_path / "test.json"
    path.write_text(json.dumps(data))
    ds = Dataset.from_json(path, name="json_test")
    assert len(ds) == 2
    assert ds.samples[1].tags == ["test"]


def test_dataset_load_from_csv(tmp_path: Path):
    path = tmp_path / "test.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["input", "expected_output"])
        writer.writeheader()
        writer.writerow({"input": "Q1", "expected_output": "A1"})
        writer.writerow({"input": "Q2", "expected_output": "A2"})
    ds = Dataset.from_csv(path, name="csv_test")
    assert len(ds) == 2


def test_dataset_save_to_json(tmp_path: Path):
    samples = [EvalSample(input="Q1", expected_output="A1")]
    ds = Dataset(name="save_test", samples=samples)
    path = tmp_path / "output.json"
    ds.to_json(path)
    loaded = json.loads(path.read_text())
    assert len(loaded) == 1
    assert loaded[0]["input"] == "Q1"
