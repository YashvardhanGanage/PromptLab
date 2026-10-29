from typing import Optional, Any
from pydantic import BaseModel, Field

# --- Prompt Schemas ---
class PromptCreate(BaseModel):
    experiment_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    system_prompt: str = ""
    user_template: str = "{input}"
    output_format: str = "labels"  # "labels", "json", "free_text"
    valid_labels: list[str] = ["positive", "negative", "neutral"]
    json_schema: dict[str, Any] = {}

class PromptUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    user_template: Optional[str] = None
    output_format: Optional[str] = None
    valid_labels: Optional[list[str]] = None
    json_schema: Optional[dict[str, Any]] = None

class PromptResponse(BaseModel):
    id: str
    experiment_id: Optional[str]
    version_num: int
    name: str
    system_prompt: str
    user_template: str
    output_format: str
    valid_labels: list[str]
    json_schema: dict[str, Any]
    content_hash: str
    is_best: bool
    created_at: str

class PromptSingleRunRequest(BaseModel):
    system_prompt: str = ""
    user_template: str = "{input}"
    input_text: str
    expected_output: Optional[str] = None
    output_format: str = "labels"
    valid_labels: list[str] = ["positive", "negative", "neutral"]
    model: Optional[str] = None
    temperature: float = 0.0

class PromptSingleRunResponse(BaseModel):
    input_text: str
    raw_output: str
    parsed_output: str
    expected_output: Optional[str]
    is_correct: Optional[bool]
    is_valid: bool
    latency_ms: float
    error_message: Optional[str] = None

# --- Experiment Schemas ---
class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = ""
    task_type: str = "classification"
    model: str = "llama3.2:1b"
    objective: str = "maximize_accuracy"
    initial_system_prompt: str = "You are a sentiment analysis assistant. Classify the sentiment of the text as positive, negative, or neutral."
    initial_user_template: str = "Text: {input}\nSentiment:"
    valid_labels: list[str] = ["positive", "negative", "neutral"]

class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    model: Optional[str] = None

class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    task_type: str
    model: str
    objective: str
    config_json: dict[str, Any]
    created_at: str
    updated_at: str
    prompts_count: Optional[int] = 0
    best_prompt: Optional[PromptResponse] = None

# --- Dataset Schemas ---
class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    input_column: str = "input"
    expected_output_column: str = "expected_output"
    train_split_ratio: float = 0.7

class DatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    filename: Optional[str]
    content_hash: str
    total_examples: int
    train_count: int
    test_count: int
    schema_info: dict[str, Any]
    created_at: str

class DatasetExampleResponse(BaseModel):
    id: str
    dataset_id: str
    split: str
    input_text: str
    expected_output: str
    extra_data: dict[str, Any]
    example_index: int

# --- Evaluation Schemas ---
class EvaluationCreate(BaseModel):
    experiment_id: Optional[str] = None
    prompt_id: str
    dataset_id: str
    split: str = "train"  # "train" or "test"
    model: Optional[str] = None
    temperature: float = 0.0

class EvaluationResultDetail(BaseModel):
    id: str
    example_id: Optional[str]
    input_text: str
    expected_output: str
    raw_output: Optional[str]
    parsed_output: Optional[str]
    is_correct: bool
    is_valid: bool
    latency_ms: float
    error_message: Optional[str]
    failure_type: Optional[str]

class EvaluationResponse(BaseModel):
    id: str
    experiment_id: Optional[str]
    prompt_id: str
    prompt_name: Optional[str] = None
    dataset_id: str
    dataset_name: Optional[str] = None
    split: str
    model: str
    status: str
    total_examples: int
    successful_examples: int
    failed_examples: int
    correct_predictions: int
    invalid_outputs: int
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    duration_ms: float
    confusion_matrix: dict[str, Any]
    error_message: Optional[str]
    created_at: str
    results: Optional[list[EvaluationResultDetail]] = None

# --- Prompt Comparison Schemas ---
class PromptComparisonRequest(BaseModel):
    baseline_eval_id: str
    candidate_eval_id: str

class ExampleDifference(BaseModel):
    input_text: str
    expected_output: str
    baseline_output: Optional[str]
    candidate_output: Optional[str]
    baseline_correct: bool
    candidate_correct: bool
    status: str  # "improved", "regressed", "both_correct", "both_incorrect"

class PromptComparisonResponse(BaseModel):
    baseline_eval_id: str
    candidate_eval_id: str
    baseline_prompt_name: str
    candidate_prompt_name: str
    accuracy_diff: float
    f1_diff: float
    latency_diff_ms: float
    invalid_outputs_diff: int
    improved_examples: list[ExampleDifference]
    regressed_examples: list[ExampleDifference]
    decision_recommendation: str
    rationale: str

# --- Agent Schemas ---
class AgentRunCreate(BaseModel):
    experiment_id: str
    dataset_id: str
    baseline_prompt_id: Optional[str] = None
    objective: str = "maximize_accuracy"  # "maximize_accuracy", "minimize_invalid_outputs", "minimize_latency_with_threshold", "balanced"
    max_iterations: int = 3

class AgentIterationResponse(BaseModel):
    id: str
    iteration_num: int
    strategy_chosen: str
    candidate_prompt_id: str
    candidate_prompt_name: Optional[str]
    candidate_eval_id: str
    decision: str  # "accepted", "rejected"
    decision_rationale: str
    metrics: dict[str, Any]
    created_at: str

class AgentToolLogResponse(BaseModel):
    id: str
    iteration_num: int
    tool_name: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    execution_time_ms: float
    created_at: str

class AgentRunResponse(BaseModel):
    id: str
    experiment_id: str
    dataset_id: str
    baseline_prompt_id: str
    best_prompt_id: Optional[str]
    baseline_eval_id: Optional[str]
    final_heldout_eval_id: Optional[str]
    status: str
    objective: str
    max_iterations: int
    current_iteration: int
    stop_reason: Optional[str]
    failure_analysis: dict[str, Any]
    created_at: str
    completed_at: Optional[str]
    iterations: Optional[list[AgentIterationResponse]] = None
    tool_logs: Optional[list[AgentToolLogResponse]] = None

# --- Failure Analysis Schemas ---
class FailurePattern(BaseModel):
    category: str
    count: int
    examples: list[dict[str, Any]]
    hypothesis: str
    recommended_strategy: str
    expected_metric_impact: str
    potential_tradeoffs: str

class FailureAnalysisReport(BaseModel):
    evaluation_id: str
    total_failures: int
    failure_rate: float
    patterns: list[FailurePattern]

# --- Dashboard Schemas ---
class DashboardStatsResponse(BaseModel):
    total_experiments: int
    total_evaluations: int
    total_agent_runs: int
    best_prompt_name: Optional[str]
    best_prompt_accuracy: Optional[float]
    latest_evaluations: list[EvaluationResponse]
    recent_regressions: list[dict[str, Any]]
    accuracy_trend: list[dict[str, Any]]
    latency_trend: list[dict[str, Any]]
    model_status: dict[str, Any]
