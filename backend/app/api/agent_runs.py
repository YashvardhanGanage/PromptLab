from fastapi import APIRouter, HTTPException
from app.schemas import AgentRunCreate
from app.agent_engine import AgentOptimizer

router = APIRouter(prefix="/agent-runs", tags=["Agent Optimizer"])

@router.post("", response_model=dict)
def create_agent_run(req: AgentRunCreate):
    try:
        run_id = AgentOptimizer.run(
            experiment_id=req.experiment_id,
            dataset_id=req.dataset_id,
            baseline_prompt_id=req.baseline_prompt_id,
            objective=req.objective,
            max_iterations=min(req.max_iterations, 10)
        )
        return {"run_id": run_id, "status": "running"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent run: {str(e)}")

@router.get("", response_model=list[dict])
def list_agent_runs(experiment_id: str = None):
    return AgentOptimizer.list_runs(experiment_id=experiment_id)

@router.get("/{run_id}", response_model=dict)
def get_agent_run(run_id: str):
    run = AgentOptimizer.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run
