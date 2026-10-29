import uuid
import time
import json
import numpy as np
from datetime import datetime, timezone
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from app.database import get_db
from app.llm_client import llm_client

def parse_output(raw_output: str, output_format: str, valid_labels: list[str]) -> tuple[str, bool, str | None]:
    """
    Parse model output and check validity.
    Returns: (parsed_value, is_valid, failure_type)
    """
    cleaned = raw_output.strip()
    if not cleaned:
        return "", False, "EMPTY_RESPONSE"

    if output_format == "labels":
        lower_raw = cleaned.lower()
        # Look for exact label matches or word boundaries
        matching_labels = [label for label in valid_labels if label.lower() in lower_raw]
        if len(matching_labels) == 1:
            # Check if there is extra fluff or if it's strict
            # If the output contains excessive waffling, mark invalid if required
            label = matching_labels[0].lower()
            # If the raw output is much longer than the label (e.g. "The sentiment is positive because..."),
            # it might still extract the label, but if words conflict or exceed limits:
            if len(cleaned.split()) > 6:
                return label, False, "EXCESSIVE_VERBOSITY"
            return label, True, None
        elif len(matching_labels) > 1:
            # Ambiguous output containing multiple valid labels
            return cleaned, False, "AMBIGUOUS_MULTIPLE_LABELS"
        else:
            return cleaned, False, "INVALID_LABEL"

    elif output_format == "json":
        try:
            parsed = json.loads(cleaned)
            return json.dumps(parsed), True, None
        except Exception:
            return cleaned, False, "MALFORMED_JSON"

    # Free text / generic
    return cleaned, True, None

class EvaluationEngine:
    @staticmethod
    def run_evaluation(
        prompt_id: str,
        dataset_id: str,
        split: str = "train",
        model: str = None,
        temperature: float = 0.0,
        experiment_id: str = None
    ) -> dict:
        """Execute a full evaluation run across a dataset split."""
        eval_id = f"eval-{uuid.uuid4().hex[:10]}"
        now_str = datetime.now(timezone.utc).isoformat()

        # Load prompt and dataset metadata
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            p_row = cursor.fetchone()
            if not p_row:
                raise ValueError(f"Prompt {prompt_id} not found.")

            cursor.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
            d_row = cursor.fetchone()
            if not d_row:
                raise ValueError(f"Dataset {dataset_id} not found.")

            cursor.execute("""
                SELECT * FROM dataset_examples 
                WHERE dataset_id = ? AND split = ? 
                ORDER BY example_index ASC
            """, (dataset_id, split))
            examples = cursor.fetchall()

            if not examples:
                raise ValueError(f"No examples found for dataset {dataset_id} in split '{split}'.")

            model_name = model or "llama3.2:1b"
            valid_labels = json.loads(p_row["valid_labels_json"] or "[]")
            output_format = p_row["output_format"]
            system_prompt = p_row["system_prompt"]
            user_template = p_row["user_template"]

            # Initialize pending evaluation record
            cursor.execute("""
                INSERT INTO evaluations (
                    id, experiment_id, prompt_id, dataset_id, split, model,
                    model_config_json, status, total_examples, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eval_id,
                experiment_id or p_row["experiment_id"],
                prompt_id,
                dataset_id,
                split,
                model_name,
                json.dumps({"temperature": temperature}),
                "running",
                len(examples),
                now_str
            ))

        total_examples = len(examples)
        successful_examples = 0
        failed_examples = 0
        correct_predictions = 0
        invalid_outputs = 0
        latencies = []

        y_true = []
        y_pred = []
        example_results = []
        overall_start = time.perf_counter()

        try:
            for ex in examples:
                ex_id = ex["id"]
                inp_text = ex["input_text"]
                exp_text = ex["expected_output"].strip().lower()

                # Format user prompt
                formatted_user_prompt = user_template.replace("{input}", inp_text)

                try:
                    raw_out, latency_ms = llm_client.generate_sync(
                        prompt=formatted_user_prompt,
                        system=system_prompt,
                        model=model_name,
                        temperature=temperature
                    )
                    latencies.append(latency_ms)

                    parsed_val, is_valid, fail_type = parse_output(raw_out, output_format, valid_labels)
                    is_correct = (parsed_val.strip().lower() == exp_text) if is_valid else False

                    if is_valid:
                        if is_correct:
                            correct_predictions += 1
                        else:
                            fail_type = "WRONG_CLASSIFICATION"
                    else:
                        invalid_outputs += 1

                    successful_examples += 1
                    y_true.append(exp_text)
                    y_pred.append(parsed_val.strip().lower() if is_valid else "INVALID_OUTPUT")

                    result_record = {
                        "id": f"res-{uuid.uuid4().hex[:10]}",
                        "evaluation_id": eval_id,
                        "example_id": ex_id,
                        "input_text": inp_text,
                        "expected_output": exp_text,
                        "raw_output": raw_out,
                        "parsed_output": parsed_val,
                        "is_correct": 1 if is_correct else 0,
                        "is_valid": 1 if is_valid else 0,
                        "latency_ms": latency_ms,
                        "error_message": None,
                        "failure_type": fail_type
                    }
                    example_results.append(result_record)

                except Exception as ex_err:
                    failed_examples += 1
                    example_results.append({
                        "id": f"res-{uuid.uuid4().hex[:10]}",
                        "evaluation_id": eval_id,
                        "example_id": ex_id,
                        "input_text": inp_text,
                        "expected_output": exp_text,
                        "raw_output": "",
                        "parsed_output": "",
                        "is_correct": 0,
                        "is_valid": 0,
                        "latency_ms": 0.0,
                        "error_message": str(ex_err),
                        "failure_type": "RUNTIME_ERROR"
                    })

            overall_duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)

            # Compute scikit-learn metrics
            if successful_examples > 0:
                acc = accuracy_score(y_true, [p if p == t else "OTHER" for p, t in zip(y_pred, y_true)])
                # Calculate macro precision, recall, f1
                prec, rec, f1, _ = precision_recall_fscore_support(
                    y_true,
                    [p if p in valid_labels else "INVALID" for p in y_pred],
                    average="macro",
                    zero_division=0
                )
                # Compute confusion matrix for known labels
                classes = sorted(list(set(valid_labels + [y for y in y_true if y in valid_labels])))
                cm = confusion_matrix(
                    y_true,
                    [p if p in classes else classes[0] for p in y_pred],
                    labels=classes
                ).tolist()
                cm_data = {"labels": classes, "matrix": cm}
            else:
                acc, prec, rec, f1 = 0.0, 0.0, 0.0, 0.0
                cm_data = {"labels": [], "matrix": []}

            # Latency metrics
            avg_lat = float(np.mean(latencies)) if latencies else 0.0
            med_lat = float(np.median(latencies)) if latencies else 0.0
            p95_lat = float(np.percentile(latencies, 95)) if len(latencies) >= 5 else avg_lat
            err_rate = round(failed_examples / total_examples, 4) if total_examples > 0 else 0.0

            # Store example-level results and update evaluation
            with get_db() as conn:
                cursor = conn.cursor()
                for r in example_results:
                    cursor.execute("""
                        INSERT INTO evaluation_results (
                            id, evaluation_id, example_id, input_text, expected_output,
                            raw_output, parsed_output, is_correct, is_valid, latency_ms,
                            error_message, failure_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r["id"], r["evaluation_id"], r["example_id"], r["input_text"],
                        r["expected_output"], r["raw_output"], r["parsed_output"],
                        r["is_correct"], r["is_valid"], r["latency_ms"],
                        r["error_message"], r["failure_type"]
                    ))

                cursor.execute("""
                    UPDATE evaluations SET
                        status = 'completed',
                        successful_examples = ?,
                        failed_examples = ?,
                        correct_predictions = ?,
                        invalid_outputs = ?,
                        accuracy = ?,
                        macro_precision = ?,
                        macro_recall = ?,
                        macro_f1 = ?,
                        avg_latency_ms = ?,
                        median_latency_ms = ?,
                        p95_latency_ms = ?,
                        error_rate = ?,
                        duration_ms = ?,
                        confusion_matrix_json = ?
                    WHERE id = ?
                """, (
                    successful_examples,
                    failed_examples,
                    correct_predictions,
                    invalid_outputs,
                    round(float(acc), 4),
                    round(float(prec), 4),
                    round(float(rec), 4),
                    round(float(f1), 4),
                    round(avg_lat, 2),
                    round(med_lat, 2),
                    round(p95_lat, 2),
                    err_rate,
                    overall_duration_ms,
                    json.dumps(cm_data),
                    eval_id
                ))

            return EvaluationEngine.get_evaluation(eval_id, include_results=True)

        except Exception as top_err:
            # Preserve partial state
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE evaluations SET
                        status = 'failed',
                        error_message = ?
                    WHERE id = ?
                """, (str(top_err), eval_id))
            raise

    @staticmethod
    def get_evaluation(eval_id: str, include_results: bool = False) -> dict | None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, p.name as prompt_name, d.name as dataset_name 
                FROM evaluations e
                JOIN prompts p ON e.prompt_id = p.id
                JOIN datasets d ON e.dataset_id = d.id
                WHERE e.id = ?
            """, (eval_id,))
            r = cursor.fetchone()
            if not r:
                return None

            data = {
                "id": r["id"],
                "experiment_id": r["experiment_id"],
                "prompt_id": r["prompt_id"],
                "prompt_name": r["prompt_name"],
                "dataset_id": r["dataset_id"],
                "dataset_name": r["dataset_name"],
                "split": r["split"],
                "model": r["model"],
                "status": r["status"],
                "total_examples": r["total_examples"],
                "successful_examples": r["successful_examples"],
                "failed_examples": r["failed_examples"],
                "correct_predictions": r["correct_predictions"],
                "invalid_outputs": r["invalid_outputs"],
                "accuracy": r["accuracy"],
                "macro_precision": r["macro_precision"],
                "macro_recall": r["macro_recall"],
                "macro_f1": r["macro_f1"],
                "avg_latency_ms": r["avg_latency_ms"],
                "median_latency_ms": r["median_latency_ms"],
                "p95_latency_ms": r["p95_latency_ms"],
                "error_rate": r["error_rate"],
                "duration_ms": r["duration_ms"],
                "confusion_matrix": json.loads(r["confusion_matrix_json"] or "{}"),
                "error_message": r["error_message"],
                "created_at": r["created_at"]
            }

            if include_results:
                cursor.execute("""
                    SELECT * FROM evaluation_results 
                    WHERE evaluation_id = ? 
                    ORDER BY id ASC
                """, (eval_id,))
                res_rows = cursor.fetchall()
                data["results"] = [
                    {
                        "id": res["id"],
                        "example_id": res["example_id"],
                        "input_text": res["input_text"],
                        "expected_output": res["expected_output"],
                        "raw_output": res["raw_output"],
                        "parsed_output": res["parsed_output"],
                        "is_correct": bool(res["is_correct"]),
                        "is_valid": bool(res["is_valid"]),
                        "latency_ms": res["latency_ms"],
                        "error_message": res["error_message"],
                        "failure_type": res["failure_type"]
                    }
                    for res in res_rows
                ]

            return data

    @staticmethod
    def list_evaluations(experiment_id: str = None, prompt_id: str = None, limit: int = 50) -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT e.*, p.name as prompt_name, d.name as dataset_name 
                FROM evaluations e
                JOIN prompts p ON e.prompt_id = p.id
                JOIN datasets d ON e.dataset_id = d.id
            """
            params = []
            conditions = []
            if experiment_id:
                conditions.append("e.experiment_id = ?")
                params.append(experiment_id)
            if prompt_id:
                conditions.append("e.prompt_id = ?")
                params.append(prompt_id)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY e.created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "experiment_id": r["experiment_id"],
                    "prompt_id": r["prompt_id"],
                    "prompt_name": r["prompt_name"],
                    "dataset_id": r["dataset_id"],
                    "dataset_name": r["dataset_name"],
                    "split": r["split"],
                    "model": r["model"],
                    "status": r["status"],
                    "total_examples": r["total_examples"],
                    "successful_examples": r["successful_examples"],
                    "failed_examples": r["failed_examples"],
                    "correct_predictions": r["correct_predictions"],
                    "invalid_outputs": r["invalid_outputs"],
                    "accuracy": r["accuracy"],
                    "macro_precision": r["macro_precision"],
                    "macro_recall": r["macro_recall"],
                    "macro_f1": r["macro_f1"],
                    "avg_latency_ms": r["avg_latency_ms"],
                    "median_latency_ms": r["median_latency_ms"],
                    "p95_latency_ms": r["p95_latency_ms"],
                    "error_rate": r["error_rate"],
                    "duration_ms": r["duration_ms"],
                    "confusion_matrix": json.loads(r["confusion_matrix_json"] or "{}"),
                    "error_message": r["error_message"],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]
