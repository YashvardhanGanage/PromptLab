import pytest
from app.database import init_db
from app.dataset_service import ensure_starter_dataset
from app.api.health import get_health
from app.api.datasets import list_datasets, get_dataset, get_dataset_examples
from app.api.experiments import create_experiment, get_experiment, list_experiments
from app.api.prompts import run_single_prompt, create_prompt
from app.api.evaluations import create_evaluation, get_failure_analysis
from app.api.dashboard import get_dashboard_stats
from app.api.export import export_evaluation, export_experiment
from app.schemas import ExperimentCreate, PromptSingleRunRequest, EvaluationCreate
from app.config import settings

def test_full_api_endpoints():
    init_db()
    ensure_starter_dataset()

    # 1. Health
    h = get_health()
    assert h["status"] == "ok"
    assert "llm" in h

    # 2. Datasets
    ds_list = list_datasets()
    assert len(ds_list) >= 1
    ds_id = ds_list[0]["id"]
    ds = get_dataset(ds_id)
    assert ds["id"] == ds_id
    exs = get_dataset_examples(ds_id, limit=5)
    assert len(exs) <= 5

    # 3. Create Experiment
    exp_req = ExperimentCreate(
        name="Integration Test Experiment",
        description="For API test coverage",
        task_type="classification",
        model="llama3.2:1b",
        objective="maximize_accuracy",
        initial_system_prompt="Classify sentiment: positive, negative, or neutral.",
        initial_user_template="Text: {input}\nSentiment:",
        valid_labels=["positive", "negative", "neutral"]
    )
    exp = create_experiment(exp_req)
    exp_id = exp["id"]
    prompt_id = exp["prompts"][0]["id"]
    assert exp_id is not None
    assert prompt_id is not None

    # 4. Single prompt execution
    single_req = PromptSingleRunRequest(
        system_prompt="Output only positive or negative.",
        user_template="{input}",
        input_text="The battery life is fantastic!",
        expected_output="positive",
        output_format="labels",
        valid_labels=["positive", "negative"]
    )
    single_res = run_single_prompt(single_req)
    assert single_res.is_valid is True
    assert single_res.latency_ms >= 0

    # 5. Run Evaluation
    eval_req = EvaluationCreate(
        experiment_id=exp_id,
        prompt_id=prompt_id,
        dataset_id=ds_id,
        split="train"
    )
    eval_res = create_evaluation(eval_req)
    eval_id = eval_res["id"]
    assert eval_res["status"] == "completed"
    assert eval_res["total_examples"] > 0

    # 6. Failure analysis endpoint
    fail_data = get_failure_analysis(eval_id)
    assert "patterns" in fail_data
    assert "failure_rate" in fail_data

    # 7. Dashboard stats
    dash_data = get_dashboard_stats()
    assert dash_data["total_experiments"] >= 1
    assert dash_data["total_evaluations"] >= 1

    # 8. Export CSV
    csv_res = export_evaluation(eval_id, format="csv")
    csv_text = csv_res.body.decode("utf-8")
    assert "Example ID" in csv_text
    assert "text/csv" in csv_res.media_type

    # 9. Export JSON
    json_res = export_experiment(exp_id)
    json_text = json_res.body.decode("utf-8")
    assert exp_id in json_text
    assert "application/json" in json_res.media_type

    # 10. CORS configuration check
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "*" in settings.CORS_ORIGINS
