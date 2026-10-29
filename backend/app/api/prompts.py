import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.schemas import PromptCreate, PromptUpdate, PromptSingleRunRequest, PromptSingleRunResponse
from app.agent_tools import compute_prompt_hash
from app.llm_client import llm_client
from app.evaluation_engine import parse_output

router = APIRouter(prefix="/prompts", tags=["Prompts"])

@router.post("", response_model=dict)
def create_prompt(p: PromptCreate):
    prompt_id = f"prompt-{uuid.uuid4().hex[:10]}"
    now_str = datetime.now(timezone.utc).isoformat()
    p_hash = compute_prompt_hash(p.system_prompt, p.user_template)

    with get_db() as conn:
        cursor = conn.cursor()
        next_v = 1
        if p.experiment_id:
            cursor.execute("SELECT MAX(version_num) as max_v FROM prompts WHERE experiment_id = ?", (p.experiment_id,))
            v_row = cursor.fetchone()
            if v_row and v_row["max_v"]:
                next_v = v_row["max_v"] + 1

        cursor.execute("""
            INSERT INTO prompts (
                id, experiment_id, version_num, name, system_prompt, user_template,
                output_format, valid_labels_json, json_schema_json, content_hash, is_best, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (
            prompt_id,
            p.experiment_id,
            next_v,
            p.name,
            p.system_prompt,
            p.user_template,
            p.output_format,
            json.dumps(p.valid_labels),
            json.dumps(p.json_schema),
            p_hash,
            now_str
        ))

    return get_prompt(prompt_id)

@router.get("/{prompt_id}", response_model=dict)
def get_prompt(prompt_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Prompt not found")

        return {
            "id": r["id"],
            "experiment_id": r["experiment_id"],
            "version_num": r["version_num"],
            "name": r["name"],
            "system_prompt": r["system_prompt"],
            "user_template": r["user_template"],
            "output_format": r["output_format"],
            "valid_labels": json.loads(r["valid_labels_json"] or "[]"),
            "json_schema": json.loads(r["json_schema_json"] or "{}"),
            "content_hash": r["content_hash"],
            "is_best": bool(r["is_best"]),
            "created_at": r["created_at"]
        }

@router.put("/{prompt_id}", response_model=dict)
def update_prompt(prompt_id: str, payload: PromptUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        p = cursor.fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Prompt not found")

        name = payload.name if payload.name is not None else p["name"]
        sys_prompt = payload.system_prompt if payload.system_prompt is not None else p["system_prompt"]
        usr_template = payload.user_template if payload.user_template is not None else p["user_template"]
        fmt = payload.output_format if payload.output_format is not None else p["output_format"]
        labels = payload.valid_labels if payload.valid_labels is not None else json.loads(p["valid_labels_json"] or "[]")
        schema = payload.json_schema if payload.json_schema is not None else json.loads(p["json_schema_json"] or "{}")

        p_hash = compute_prompt_hash(sys_prompt, usr_template)

        cursor.execute("""
            UPDATE prompts SET
                name = ?, system_prompt = ?, user_template = ?,
                output_format = ?, valid_labels_json = ?, json_schema_json = ?,
                content_hash = ?
            WHERE id = ?
        """, (name, sys_prompt, usr_template, fmt, json.dumps(labels), json.dumps(schema), p_hash, prompt_id))

    return get_prompt(prompt_id)

@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    return {"status": "success", "message": f"Prompt {prompt_id} deleted"}

@router.post("/run-single", response_model=PromptSingleRunResponse)
def run_single_prompt(req: PromptSingleRunRequest):
    formatted = req.user_template.replace("{input}", req.input_text)
    try:
        raw_out, latency_ms = llm_client.generate_sync(
            prompt=formatted,
            system=req.system_prompt,
            model=req.model,
            temperature=req.temperature
        )
        parsed, is_valid, fail_type = parse_output(raw_out, req.output_format, req.valid_labels)
        is_correct = None
        if req.expected_output:
            is_correct = (parsed.strip().lower() == req.expected_output.strip().lower()) if is_valid else False

        return PromptSingleRunResponse(
            input_text=req.input_text,
            raw_output=raw_out,
            parsed_output=parsed,
            expected_output=req.expected_output,
            is_correct=is_correct,
            is_valid=is_valid,
            latency_ms=latency_ms,
            error_message=fail_type
        )
    except Exception as e:
        return PromptSingleRunResponse(
            input_text=req.input_text,
            raw_output="",
            parsed_output="",
            expected_output=req.expected_output,
            is_correct=False,
            is_valid=False,
            latency_ms=0.0,
            error_message=str(e)
        )
