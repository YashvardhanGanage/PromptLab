import pytest
from app.database import init_db
from app.dataset_service import ensure_starter_dataset
from app.agent_tools import compute_prompt_hash
from app.database import get_db
from app.evaluation_engine import EvaluationEngine
from app.failure_analysis import FailureAnalysisService
from app.agent_tools import AgentTools

def test_full_evaluation_run():
    init_db()
    ensure_starter_dataset()

    # Create test prompt
    prompt_id = "test-prompt-baseline"
    p_hash = compute_prompt_hash("You are a sentiment analyzer.", "Text: {input}\nSentiment:")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        cursor.execute("""
            INSERT INTO prompts (
                id, experiment_id, version_num, name, system_prompt, user_template,
                output_format, valid_labels_json, json_schema_json, content_hash, is_best, created_at
            ) VALUES (?, NULL, 1, 'Baseline Prompt', 'You are a sentiment analyzer.', 'Text: {input}\\nSentiment:', 'labels', '["positive", "negative", "neutral"]', '{}', ?, 1, '2026-10-29T00:00:00Z')
        """, (prompt_id, p_hash))

    # Evaluate on tuning split
    eval_result = EvaluationEngine.run_evaluation(
        prompt_id=prompt_id,
        dataset_id="starter-sentiment-dataset",
        split="train"
    )

    assert eval_result is not None
    assert eval_result["status"] == "completed"
    assert eval_result["total_examples"] == 20
    assert eval_result["successful_examples"] == 20
    assert eval_result["accuracy"] >= 0.0
    assert "matrix" in eval_result["confusion_matrix"]
    assert len(eval_result["results"]) == 20

    # Failure analysis
    failures = FailureAnalysisService.analyze_evaluation(eval_result["id"])
    assert "patterns" in failures
    assert failures["evaluation_id"] == eval_result["id"]

def test_candidate_comparison():
    init_db()
    ensure_starter_dataset()

    # Create candidate prompt
    cand_prompt_id = "test-prompt-candidate"
    p_hash2 = compute_prompt_hash("Return ONLY one word: positive, negative, or neutral.", "{input}\nSentiment:")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prompts WHERE id = ?", (cand_prompt_id,))
        cursor.execute("""
            INSERT INTO prompts (
                id, experiment_id, version_num, name, system_prompt, user_template,
                output_format, valid_labels_json, json_schema_json, content_hash, is_best, created_at
            ) VALUES (?, NULL, 2, 'Strict Candidate', 'Return ONLY one word: positive, negative, or neutral.', '{input}\\nSentiment:', 'labels', '["positive", "negative", "neutral"]', '{}', ?, 0, '2026-10-29T00:00:00Z')
        """, (cand_prompt_id, p_hash2))

    eval_cand = EvaluationEngine.run_evaluation(
        prompt_id=cand_prompt_id,
        dataset_id="starter-sentiment-dataset",
        split="train"
    )

    # Compare against baseline
    eval_base = EvaluationEngine.run_evaluation(
        prompt_id="test-prompt-baseline",
        dataset_id="starter-sentiment-dataset",
        split="train"
    )

    comparison = AgentTools.compare_candidates(
        baseline_eval_id=eval_base["id"],
        candidate_eval_id=eval_cand["id"],
        objective="maximize_accuracy"
    )

    assert "decision" in comparison
    assert comparison["decision"] in ("accepted", "rejected")
    assert "rationale" in comparison
    assert "improved_examples" in comparison
    assert "regressed_examples" in comparison
