import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.schemas import ExperimentCreate, ExperimentUpdate, ExperimentResponse
from app.agent_tools import compute_prompt_hash

router = APIRouter(prefix="/experiments", tags=["Experiments"])

@router.get("", response_model=list[dict])
def list_experiments():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experiments ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            cursor.execute("SELECT COUNT(*) as count FROM prompts WHERE experiment_id = ?", (r["id"],))
            p_count = cursor.fetchone()["count"]
            cursor.execute("SELECT * FROM prompts WHERE experiment_id = ? AND is_best = 1", (r["id"],))
            best_p = cursor.fetchone()
            result.append({
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "task_type": r["task_type"],
                "model": r["model"],
                "objective": r["objective"],
                "config_json": json.loads(r["config_json"] or "{}"),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "prompts_count": p_count,
                "best_prompt": dict(best_p) if best_p else None
            })
        return result

@router.post("", response_model=dict)
def create_experiment(exp: ExperimentCreate):
    exp_id = f"exp-{uuid.uuid4().hex[:10]}"
    prompt_id = f"prompt-{uuid.uuid4().hex[:10]}"
    now_str = datetime.now(timezone.utc).isoformat()

    p_hash = compute_prompt_hash(exp.initial_system_prompt, exp.initial_user_template)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO experiments (id, name, description, task_type, model, objective, config_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_id, exp.name, exp.description, exp.task_type, exp.model, exp.objective,
            json.dumps({"valid_labels": exp.valid_labels}), now_str, now_str
        ))

        cursor.execute("""
            INSERT INTO prompts (
                id, experiment_id, version_num, name, system_prompt, user_template,
                output_format, valid_labels_json, json_schema_json, content_hash, is_best, created_at
            ) VALUES (?, ?, 1, ?, ?, ?, 'labels', ?, '{}', ?, 1, ?)
        """, (
            prompt_id, exp_id, f"{exp.name} (v1 Baseline)", exp.initial_system_prompt,
            exp.initial_user_template, json.dumps(exp.valid_labels), p_hash, now_str
        ))

    return get_experiment(exp_id)

@router.get("/{experiment_id}", response_model=dict)
def get_experiment(experiment_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Experiment not found")

        cursor.execute("SELECT * FROM prompts WHERE experiment_id = ? ORDER BY version_num ASC", (experiment_id,))
        prompts = [
            {
                "id": p["id"],
                "experiment_id": p["experiment_id"],
                "version_num": p["version_num"],
                "name": p["name"],
                "system_prompt": p["system_prompt"],
                "user_template": p["user_template"],
                "output_format": p["output_format"],
                "valid_labels": json.loads(p["valid_labels_json"] or "[]"),
                "json_schema": json.loads(p["json_schema_json"] or "{}"),
                "content_hash": p["content_hash"],
                "is_best": bool(p["is_best"]),
                "created_at": p["created_at"]
            }
            for p in cursor.fetchall()
        ]

        best_prompt = next((p for p in prompts if p["is_best"]), (prompts[0] if prompts else None))

        return {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "task_type": r["task_type"],
            "model": r["model"],
            "objective": r["objective"],
            "config_json": json.loads(r["config_json"] or "{}"),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "prompts": prompts,
            "best_prompt": best_prompt
        }

@router.put("/{experiment_id}", response_model=dict)
def update_experiment(experiment_id: str, payload: ExperimentUpdate):
    now_str = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Experiment not found")

        updates = []
        params = []
        if payload.name is not None:
            updates.append("name = ?")
            params.append(payload.name)
        if payload.description is not None:
            updates.append("description = ?")
            params.append(payload.description)
        if payload.objective is not None:
            updates.append("objective = ?")
            params.append(payload.objective)
        if payload.model is not None:
            updates.append("model = ?")
            params.append(payload.model)

        if updates:
            updates.append("updated_at = ?")
            params.append(now_str)
            params.append(experiment_id)
            cursor.execute(f"UPDATE experiments SET {', '.join(updates)} WHERE id = ?", params)

    return get_experiment(experiment_id)

@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
    return {"status": "success", "message": f"Experiment {experiment_id} deleted"}
