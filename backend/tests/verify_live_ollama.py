import os
import sys
import json
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Explicitly ensure MOCK_LLM is false for this live verification
os.environ["MOCK_LLM"] = "false"

from app.config import settings
settings.MOCK_LLM = False

from app.llm_client import LLMClient
from app.evaluation_engine import parse_output
from app.api.prompts import run_single_prompt
from app.schemas import PromptSingleRunRequest
from app.database import init_db

def run_live_verification():
    print("=" * 60)
    print("PROMPTLAB LIVE OLLAMA VERIFICATION (MOCK_LLM=false)")
    print("=" * 60)

    init_db()
    client = LLMClient()
    client.force_mock = False

    # 1. Connection check
    diag = client.check_connection_sync()
    print(f"\n[1] Ollama Connection Status: {diag['status']}")
    print(f"    Base URL: {diag['base_url']}")
    print(f"    Available Models: {diag.get('models', [])}")
    print(f"    Default Model Available ({diag.get('default_model')}): {diag.get('default_model_available')}")
    assert diag["status"] == "connected", f"Ollama is not connected: {diag.get('error')}"
    assert diag.get("default_model_available"), f"Model {diag.get('default_model')} not found in Ollama!"

    # 2. Live Generation Call with llama3.2:1b
    print(f"\n[2] Executing Live Inference with {client.default_model}...")
    prompt = "Review: The battery life on this laptop is phenomenal and exceeds expectations.\nSentiment (positive/negative/neutral):"
    system = "You are a sentiment classifier. Output strictly one word: positive, negative, or neutral."

    raw_output, latency_ms = client.generate_sync(
        prompt=prompt,
        system=system,
        model="llama3.2:1b",
        temperature=0.0
    )
    print(f"    Raw Output from Ollama: '{raw_output}'")
    print(f"    Live Latency: {latency_ms:.2f} ms")
    assert raw_output, "Ollama returned empty response!"

    # 3. Output Validation on Live Response
    valid_labels = ["positive", "negative", "neutral"]
    parsed_val, is_valid, failure_type = parse_output(raw_output, "labels", valid_labels)
    print(f"    Parsed Value: '{parsed_val}'")
    print(f"    Is Valid: {is_valid}")
    print(f"    Failure Type: {failure_type}")
    assert is_valid is True, f"Live response was unexpectedly marked invalid: {failure_type}"
    assert parsed_val == "positive", f"Expected 'positive', got '{parsed_val}'"

    # 4. Strict Output Validation Test Suite: Detecting Violations
    print(f"\n[3] Testing Format Violation Detection in Output Validator...")

    # Case A: Invalid label outside permitted set
    val, valid, fail = parse_output("delighted and joyful", "labels", valid_labels)
    print(f"    A. Out-of-vocabulary label ('delighted and joyful'): is_valid={valid}, failure_type='{fail}'")
    assert valid is False
    assert fail == "INVALID_LABEL"

    # Case B: Excessive verbosity / conversational fluff
    val, valid, fail = parse_output(
        "Based on the analysis of the linguistic features of the statement, the sentiment expressed by the user is positive.",
        "labels",
        valid_labels
    )
    print(f"    B. Excessive Verbosity: is_valid={valid}, failure_type='{fail}'")
    assert valid is False
    assert fail == "EXCESSIVE_VERBOSITY"

    # Case C: Ambiguous multiple labels
    val, valid, fail = parse_output("The customer starts positive but ends negative.", "labels", valid_labels)
    print(f"    C. Multiple Conflicting Labels: is_valid={valid}, failure_type='{fail}'")
    assert valid is False
    assert fail == "AMBIGUOUS_MULTIPLE_LABELS"

    # Case D: Empty model output
    val, valid, fail = parse_output("   ", "labels", valid_labels)
    print(f"    D. Empty Response: is_valid={valid}, failure_type='{fail}'")
    assert valid is False
    assert fail == "EMPTY_RESPONSE"

    # Case E: Structured JSON validation (Valid JSON)
    val, valid, fail = parse_output('{"sentiment": "negative", "confidence": 0.98}', "json", [])
    print(f"    E. Valid Structured JSON: is_valid={valid}, failure_type='{fail}'")
    assert valid is True
    assert fail is None

    # Case F: Structured JSON validation (Malformed JSON syntax)
    val, valid, fail = parse_output('{"sentiment": "negative", confidence: 0.98', "json", [])
    print(f"    F. Malformed JSON: is_valid={valid}, failure_type='{fail}'")
    assert valid is False
    assert fail == "MALFORMED_JSON"

    # 5. Live Single Prompt API Endpoint Test with Live Ollama
    print(f"\n[4] Testing /api/prompts/run-single Endpoint with Live Ollama...")
    req = PromptSingleRunRequest(
        system_prompt="You are a binary sentiment classifier. Output ONLY the word: positive or negative.",
        user_template="Statement: {input}\nClassification:",
        input_text="The screen shattered the very first hour out of the box, utterly useless.",
        expected_output="negative",
        valid_labels=["positive", "negative"],
        output_format="labels",
        model="llama3.2:1b"
    )
    endpoint_res = run_single_prompt(req)
    print(f"    Endpoint Response:")
    print(f"      Raw Output: '{endpoint_res.raw_output}'")
    print(f"      Parsed Output: '{endpoint_res.parsed_output}'")
    print(f"      Is Valid: {endpoint_res.is_valid}")
    print(f"      Is Correct: {endpoint_res.is_correct}")
    print(f"      Latency: {endpoint_res.latency_ms:.2f} ms")
    print(f"      Error Message: {endpoint_res.error_message}")

    assert endpoint_res.is_valid is True
    assert endpoint_res.is_correct is True
    assert endpoint_res.parsed_output == "negative"

    print("\n" + "=" * 60)
    print("ALL LIVE OLLAMA VERIFICATION & OUTPUT VALIDATION TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_live_verification()
