import pytest
from app.evaluation_engine import parse_output
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

def test_parse_output_labels_valid():
    parsed, is_valid, fail_type = parse_output("positive", "labels", ["positive", "negative", "neutral"])
    assert is_valid is True
    assert parsed == "positive"
    assert fail_type is None

def test_parse_output_labels_case_insensitive():
    parsed, is_valid, fail_type = parse_output("POSITIVE", "labels", ["positive", "negative", "neutral"])
    assert is_valid is True
    assert parsed == "positive"

def test_parse_output_labels_invalid():
    parsed, is_valid, fail_type = parse_output("completely bananas", "labels", ["positive", "negative", "neutral"])
    assert is_valid is False
    assert fail_type == "INVALID_LABEL"

def test_parse_output_labels_ambiguous():
    parsed, is_valid, fail_type = parse_output("It could be positive or negative", "labels", ["positive", "negative", "neutral"])
    assert is_valid is False
    assert fail_type == "AMBIGUOUS_MULTIPLE_LABELS"

def test_parse_output_excessive_verbosity():
    parsed, is_valid, fail_type = parse_output(
        "I believe that overall this text demonstrates a very positive sentiment regarding customer service",
        "labels",
        ["positive", "negative", "neutral"]
    )
    assert is_valid is False
    assert fail_type == "EXCESSIVE_VERBOSITY"

def test_parse_output_empty():
    parsed, is_valid, fail_type = parse_output("   ", "labels", ["positive", "negative", "neutral"])
    assert is_valid is False
    assert fail_type == "EMPTY_RESPONSE"

def test_parse_output_json_valid():
    parsed, is_valid, fail_type = parse_output('{"sentiment": "positive", "confidence": 0.95}', "json", [])
    assert is_valid is True
    assert "sentiment" in parsed

def test_parse_output_json_malformed():
    parsed, is_valid, fail_type = parse_output('{"sentiment": "positive", confidence:}', "json", [])
    assert is_valid is False
    assert fail_type == "MALFORMED_JSON"

def test_classification_metrics_computation():
    y_true = ["positive", "negative", "positive", "neutral", "negative"]
    y_pred = ["positive", "negative", "neutral", "neutral", "negative"]
    labels = ["positive", "negative", "neutral"]

    acc = accuracy_score(y_true, y_pred)
    assert acc == 0.8

    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    assert prec > 0.7
    assert rec > 0.7
    assert f1 > 0.7

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    assert cm.shape == (3, 3)
