import io
import csv
import json
from fastapi import APIRouter, HTTPException, Response
from app.evaluation_engine import EvaluationEngine
from app.api.experiments import get_experiment

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/evaluation/{evaluation_id}")
def export_evaluation(evaluation_id: str, format: str = "csv"):
    ev = EvaluationEngine.get_evaluation(evaluation_id, include_results=True)
    if not ev:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    if format.lower() == "json":
        return Response(
            content=json.dumps(ev, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=eval_{evaluation_id}.json"}
        )

    # Default to CSV export of example results
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Example ID", "Input Text", "Expected Output", "Raw Output",
        "Parsed Output", "Is Correct", "Is Valid", "Latency (ms)",
        "Failure Type", "Error Message"
    ])

    for r in ev.get("results", []):
        writer.writerow([
            r["example_id"],
            r["input_text"],
            r["expected_output"],
            r["raw_output"],
            r["parsed_output"],
            r["is_correct"],
            r["is_valid"],
            r["latency_ms"],
            r["failure_type"] or "",
            r["error_message"] or ""
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=eval_{evaluation_id}.csv"}
    )

@router.get("/experiment/{experiment_id}")
def export_experiment(experiment_id: str):
    exp = get_experiment(experiment_id)
    return Response(
        content=json.dumps(exp, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=experiment_{experiment_id}.json"}
    )
