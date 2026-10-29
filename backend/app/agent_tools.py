import time
import json
import uuid
import hashlib
from app.database import get_db
from app.evaluation_engine import EvaluationEngine, parse_output
from app.failure_analysis import FailureAnalysisService
from app.llm_client import llm_client

def compute_prompt_hash(system: str, template: str) -> str:
    content = f"{system.strip()}|||{template.strip()}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

class AgentTools:
    """Registered, strictly controlled typed tools for the Agentic Optimizer."""

    @staticmethod
    def evaluate_prompt(prompt_id: str, dataset_id: str, split: str = "train", experiment_id: str = None) -> dict:
        """Evaluate a prompt against a specific dataset split."""
        start = time.perf_counter()
        eval_result = EvaluationEngine.run_evaluation(
            prompt_id=prompt_id,
            dataset_id=dataset_id,
            split=split,
            experiment_id=experiment_id
        )
        return eval_result

    @staticmethod
    def inspect_failures(evaluation_id: str) -> dict:
        """Inspect and categorize failure patterns from an evaluation run."""
        return FailureAnalysisService.analyze_evaluation(evaluation_id)

    @staticmethod
    def generate_candidate(
        current_prompt_id: str,
        strategy: str,
        failure_summary: str,
        experiment_id: str
    ) -> dict:
        """Generate a revised candidate prompt using the LLM guided by observed failures and strategy."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompts WHERE id = ?", (current_prompt_id,))
            p = cursor.fetchone()
            if not p:
                raise ValueError(f"Prompt {current_prompt_id} not found")

            # Determine next version number for this experiment
            cursor.execute("SELECT MAX(version_num) as max_v FROM prompts WHERE experiment_id = ?", (experiment_id,))
            v_row = cursor.fetchone()
            next_v = (v_row["max_v"] or 1) + 1

        prompt_generation_request = f"""
You are an expert prompt engineer.
CURRENT SYSTEM PROMPT:
{p['system_prompt']}

CURRENT USER TEMPLATE:
{p['user_template']}

OBSERVED FAILURES AND EVIDENCE:
{failure_summary}

OPTIMIZATION STRATEGY TO APPLY:
{strategy}

TASK:
Produce an improved candidate prompt that directly resolves these failures while maintaining high accuracy and low latency.
Return a valid JSON object with keys:
- "name": descriptive name for this prompt version
- "system_prompt": full revised system instructions
- "user_template": user template containing "{{input}}"
"""
        raw_response, latency_ms = llm_client.generate_sync(
            prompt=prompt_generation_request,
            system="You are an expert prompt engineer. Always return clean valid JSON.",
            format_type="json"
        )

        try:
            cand_data = json.loads(raw_response)
        except Exception:
            # Fallback if raw text returned
            cand_data = {
                "name": f"Candidate v{next_v} ({strategy})",
                "system_prompt": f"{p['system_prompt']} Ensure strict adherence to labels. Output only positive, negative, or neutral.",
                "user_template": p["user_template"]
            }

        name = cand_data.get("name", f"Candidate v{next_v} ({strategy})")
        sys_prompt = cand_data.get("system_prompt", p["system_prompt"])
        usr_template = cand_data.get("user_template", p["user_template"])
        if "{input}" not in usr_template:
            usr_template = usr_template + "\nText: {input}"

        p_hash = compute_prompt_hash(sys_prompt, usr_template)
        new_prompt_id = f"prompt-{uuid.uuid4().hex[:10]}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prompts (
                    id, experiment_id, version_num, name, system_prompt, user_template,
                    output_format, valid_labels_json, json_schema_json, content_hash,
                    is_best, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                new_prompt_id,
                experiment_id,
                next_v,
                name,
                sys_prompt,
                usr_template,
                p["output_format"],
                p["valid_labels_json"],
                p["json_schema_json"],
                p_hash,
                now_str
            ))

        return {
            "id": new_prompt_id,
            "version_num": next_v,
            "name": name,
            "system_prompt": sys_prompt,
            "user_template": usr_template,
            "content_hash": p_hash
        }

    @staticmethod
    def compare_candidates(baseline_eval_id: str, candidate_eval_id: str, objective: str = "maximize_accuracy") -> dict:
        """Compare candidate evaluation vs baseline/best on identical examples."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluations WHERE id = ?", (baseline_eval_id,))
            b_eval = cursor.fetchone()
            cursor.execute("SELECT * FROM evaluations WHERE id = ?", (candidate_eval_id,))
            c_eval = cursor.fetchone()

            if not b_eval or not c_eval:
                raise ValueError("Both evaluations must exist for comparison.")

            cursor.execute("SELECT * FROM evaluation_results WHERE evaluation_id = ?", (baseline_eval_id,))
            b_results = {r["example_id"]: r for r in cursor.fetchall()}

            cursor.execute("SELECT * FROM evaluation_results WHERE evaluation_id = ?", (candidate_eval_id,))
            c_results = {r["example_id"]: r for r in cursor.fetchall()}

            cursor.execute("SELECT name FROM prompts WHERE id = ?", (b_eval["prompt_id"],))
            b_pname = cursor.fetchone()["name"]
            cursor.execute("SELECT name FROM prompts WHERE id = ?", (c_eval["prompt_id"],))
            c_pname = cursor.fetchone()["name"]

        acc_diff = round(c_eval["accuracy"] - b_eval["accuracy"], 4)
        f1_diff = round(c_eval["macro_f1"] - b_eval["macro_f1"], 4)
        lat_diff = round(c_eval["avg_latency_ms"] - b_eval["avg_latency_ms"], 2)
        inv_diff = c_eval["invalid_outputs"] - b_eval["invalid_outputs"]

        improved = []
        regressed = []

        for ex_id, b_r in b_results.items():
            c_r = c_results.get(ex_id)
            if not c_r:
                continue

            b_ok = bool(b_r["is_correct"])
            c_ok = bool(c_r["is_correct"])

            diff_item = {
                "input_text": b_r["input_text"],
                "expected_output": b_r["expected_output"],
                "baseline_output": b_r["raw_output"],
                "candidate_output": c_r["raw_output"],
                "baseline_correct": b_ok,
                "candidate_correct": c_ok,
                "status": "improved" if (not b_ok and c_ok) else ("regressed" if (b_ok and not c_ok) else ("both_correct" if b_ok else "both_incorrect"))
            }

            if not b_ok and c_ok:
                improved.append(diff_item)
            elif b_ok and not c_ok:
                regressed.append(diff_item)

        # Decide candidate acceptance based on objective
        decision = "rejected"
        rationale = ""

        if objective == "maximize_accuracy":
            if acc_diff > 0:
                decision = "accepted"
                rationale = f"Accuracy improved by +{acc_diff * 100:.1f}% ({b_eval['accuracy']:.1%} -> {c_eval['accuracy']:.1%}) with {len(improved)} improved examples vs {len(regressed)} regressed."
            elif acc_diff == 0:
                if inv_diff < 0:
                    decision = "accepted"
                    rationale = f"Accuracy matched at {c_eval['accuracy']:.1%}, but invalid outputs decreased by {abs(inv_diff)}."
                elif lat_diff < -15.0:
                    decision = "accepted"
                    rationale = f"Accuracy matched at {c_eval['accuracy']:.1%}, but average latency improved by {abs(lat_diff)}ms."
                else:
                    decision = "rejected"
                    rationale = f"No meaningful improvement in accuracy ({acc_diff * 100:.1f}%) or secondary metrics."
            else:
                decision = "rejected"
                rationale = f"Accuracy regressed by {acc_diff * 100:.1f}% ({len(regressed)} regressions)."

        elif objective == "minimize_invalid_outputs":
            if inv_diff < 0:
                decision = "accepted"
                rationale = f"Invalid outputs reduced from {b_eval['invalid_outputs']} to {c_eval['invalid_outputs']}."
            elif inv_diff == 0 and acc_diff > 0:
                decision = "accepted"
                rationale = f"Invalid outputs stayed equal, but accuracy improved by +{acc_diff * 100:.1f}%."
            else:
                decision = "rejected"
                rationale = f"Candidate did not reduce invalid outputs (diff: {inv_diff})."

        elif objective == "minimize_latency_with_threshold":
            quality_threshold = 0.75
            if c_eval["accuracy"] >= quality_threshold and lat_diff < -10.0:
                decision = "accepted"
                rationale = f"Latency reduced by {abs(lat_diff)}ms while maintaining accuracy at {c_eval['accuracy']:.1%} (>= {quality_threshold:.0%})."
            else:
                decision = "rejected"
                rationale = f"Candidate failed threshold criteria (Acc: {c_eval['accuracy']:.1%}, Latency change: {lat_diff}ms)."

        else: # "balanced"
            # score = 0.6 * acc + 0.2 * (1 - error_rate) + 0.2 * (1 - min(lat, 200)/200)
            b_score = 0.6 * b_eval["accuracy"] + 0.2 * (1.0 - (b_eval["invalid_outputs"] / max(1, b_eval["total_examples"])))
            c_score = 0.6 * c_eval["accuracy"] + 0.2 * (1.0 - (c_eval["invalid_outputs"] / max(1, c_eval["total_examples"])))
            if c_score > b_score:
                decision = "accepted"
                rationale = f"Composite balanced score improved ({b_score:.3f} -> {c_score:.3f})."
            else:
                decision = "rejected"
                rationale = f"Composite balanced score did not improve ({c_score:.3f} <= {b_score:.3f})."

        return {
            "baseline_eval_id": baseline_eval_id,
            "candidate_eval_id": candidate_eval_id,
            "baseline_prompt_name": b_pname,
            "candidate_prompt_name": c_pname,
            "accuracy_diff": acc_diff,
            "f1_diff": f1_diff,
            "latency_diff_ms": lat_diff,
            "invalid_outputs_diff": inv_diff,
            "improved_examples": improved,
            "regressed_examples": regressed,
            "decision": decision,
            "decision_recommendation": decision,
            "rationale": rationale
        }

    @staticmethod
    def validate_output(output_text: str, output_format: str, valid_labels: list[str]) -> dict:
        parsed, is_valid, fail_type = parse_output(output_text, output_format, valid_labels)
        return {
            "parsed_output": parsed,
            "is_valid": is_valid,
            "failure_type": fail_type
        }
