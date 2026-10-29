import pytest
import concurrent.futures
import functools
from unittest.mock import patch
from app.database import init_db, get_db
from app.dataset_service import ensure_starter_dataset
from app.agent_engine import AgentOptimizer
from app.agent_tools import AgentTools
from app.api.experiments import create_experiment, get_experiment
from app.schemas import ExperimentCreate
from app.llm_client import llm_client

def timeout(seconds=20):
    """Decorator to enforce a strict timeout on test execution."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"Test '{func.__name__}' timed out after {seconds} seconds. Probable cause: blocking network I/O or deadlock.")
        return wrapper
    return decorator

@timeout(seconds=20)
def test_agent_bounded_optimization_workflow():
    init_db()
    ensure_starter_dataset()

    def deterministic_generate(prompt, system="", model=None, temperature=0.0, format_type=None):
        return llm_client._mock_generate(prompt, system, model or "llama3.2:1b")

    with patch.object(llm_client, "generate_sync", side_effect=deterministic_generate), \
         patch.object(llm_client, "generate", side_effect=deterministic_generate):

        # 1. Create an experiment with naive baseline
        exp_req = ExperimentCreate(
            name="Agent Sentiment Optimization Experiment",
            description="Verify automated agent workflow and stopping criteria",
            task_type="classification",
            objective="maximize_accuracy",
            initial_system_prompt="Classify the sentiment of the text.",
            initial_user_template="{input}"
        )
        exp = create_experiment(exp_req)
        exp_id = exp["id"]
        base_prompt_id = exp["prompts"][0]["id"]

        # 2. Launch agent run synchronously with bounded budget: max_iterations=2
        max_budget = 2
        run_id = AgentOptimizer.run(
            experiment_id=exp_id,
            dataset_id="starter-sentiment-dataset",
            baseline_prompt_id=base_prompt_id,
            objective="maximize_accuracy",
            max_iterations=max_budget,
            sync=True
        )

        run = AgentOptimizer.get_run(run_id)

        # 3. Verify execution completed within budget
        assert run is not None, "Agent run was not found"
        assert run["status"] == "completed", f"Agent run failed: {run.get('stop_reason')}"
        assert run["baseline_eval_id"] is not None
        assert run["final_heldout_eval_id"] is not None
        assert run["stop_reason"] is not None
        assert len(run["iterations"]) <= max_budget, f"Agent exceeded budget! Iterations: {len(run['iterations'])}"
        assert len(run["tool_logs"]) >= 3

        # 4. Verify candidate evaluation, acceptance, and best prompt preservation
        with get_db() as conn:
            cursor = conn.cursor()
            # Verify held-out evaluation was run on test split
            cursor.execute("SELECT split FROM evaluations WHERE id = ?", (run["final_heldout_eval_id"],))
            split_row = cursor.fetchone()
            assert split_row["split"] == "test"

            # Verify original prompt was preserved without overwrite
            cursor.execute("SELECT * FROM prompts WHERE id = ?", (base_prompt_id,))
            orig_p = cursor.fetchone()
            assert orig_p["system_prompt"] == "Classify the sentiment of the text."

            # Verify best prompt exists in experiment and is marked is_best = 1
            cursor.execute("SELECT * FROM prompts WHERE experiment_id = ? AND is_best = 1", (exp_id,))
            best_p = cursor.fetchone()
            assert best_p is not None
            assert best_p["id"] == run["best_prompt_id"]

        # 5. Verify experiment persistence: retrieve and verify all prompts exist
        persisted_exp = get_experiment(exp_id)
        assert len(persisted_exp["prompts"]) >= 2, "Candidate prompts were not persisted in experiment"

@timeout(seconds=10)
def test_agent_error_handling_and_validation():
    init_db()

    # Verify error handling for non-existent experiment
    with pytest.raises(Exception):
        AgentOptimizer.run(
            experiment_id="non-existent-experiment-id",
            dataset_id="starter-sentiment-dataset",
            sync=True
        )

    # Verify error handling for non-existent prompt
    with pytest.raises(Exception):
        AgentTools.evaluate_prompt(
            prompt_id="non-existent-prompt-id",
            dataset_id="starter-sentiment-dataset"
        )
