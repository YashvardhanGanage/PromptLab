from fastapi import APIRouter, HTTPException
from app.schemas import EvaluationCreate, PromptComparisonRequest
from app.evaluation_engine import EvaluationEngine
from app.agent_tools import AgentTools
from app.failure_analysis import FailureAnalysisService

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])

@router.post("", response_model=dict)
def create_evaluation(req: EvaluationCreate):
    try:
        eval_result = EvaluationEngine.run_evaluation(
            prompt_id=req.prompt_id,
            dataset_id=req.dataset_id,
            split=req.split,
            model=req.model,
            temperature=req.temperature,
            experiment_id=req.experiment_id
        )
        return eval_result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.get("", response_model=list[dict])
def list_evaluations(experiment_id: str = None, prompt_id: str = None, limit: int = 50):
    return EvaluationEngine.list_evaluations(experiment_id=experiment_id, prompt_id=prompt_id, limit=limit)

@router.get("/{evaluation_id}", response_model=dict)
def get_evaluation(evaluation_id: str, include_results: bool = True):
    ev = EvaluationEngine.get_evaluation(evaluation_id, include_results=include_results)
    if not ev:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return ev

@router.post("/compare", response_model=dict)
def compare_prompts(req: PromptComparisonRequest, objective: str = "maximize_accuracy"):
    try:
        comp = AgentTools.compare_candidates(
            baseline_eval_id=req.baseline_eval_id,
            candidate_eval_id=req.candidate_eval_id,
            objective=objective
        )
        return comp
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/{evaluation_id}/failures", response_model=dict)
def get_failure_analysis(evaluation_id: str):
    ev = EvaluationEngine.get_evaluation(evaluation_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return FailureAnalysisService.analyze_evaluation(evaluation_id)
