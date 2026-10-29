import threading
import uuid
import json
import time
from datetime import datetime, timezone
from app.database import get_db
from app.agent_tools import AgentTools, compute_prompt_hash
from app.evaluation_engine import EvaluationEngine

class AgentOptimizer:
    """
    Bounded Agentic Optimization Engine.
    Executes a structured, evidence-based optimization loop using controlled tools.
    """
    active_threads: dict = {}

    @staticmethod
    def run(
        experiment_id: str,
        dataset_id: str,
        baseline_prompt_id: str = None,
        objective: str = "maximize_accuracy",
        max_iterations: int = 3,
        sync: bool = False
    ) -> str:
        """Create and execute an agent optimization run in the background (or synchronously if sync=True)."""
        run_id = f"agent-run-{uuid.uuid4().hex[:10]}"
        now_str = datetime.now(timezone.utc).isoformat()

        # If baseline prompt not specified, retrieve best or latest prompt for experiment
        with get_db() as conn:
            cursor = conn.cursor()
            if not baseline_prompt_id:
                cursor.execute("""
                    SELECT id FROM prompts 
                    WHERE experiment_id = ? 
                    ORDER BY is_best DESC, version_num DESC LIMIT 1
                """, (experiment_id,))
                p_row = cursor.fetchone()
                if not p_row:
                    raise ValueError(f"No prompt found for experiment {experiment_id}")
                baseline_prompt_id = p_row["id"]

            cursor.execute("""
                INSERT INTO agent_runs (
                    id, experiment_id, dataset_id, baseline_prompt_id, best_prompt_id,
                    status, objective, max_iterations, current_iteration, created_at
                ) VALUES (?, ?, ?, ?, ?, 'running', ?, ?, 0, ?)
            """, (
                run_id,
                experiment_id,
                dataset_id,
                baseline_prompt_id,
                baseline_prompt_id,
                objective,
                max_iterations,
                now_str
            ))

        if sync:
            AgentOptimizer._execute_workflow(
                run_id=run_id,
                experiment_id=experiment_id,
                dataset_id=dataset_id,
                baseline_prompt_id=baseline_prompt_id,
                objective=objective,
                max_iterations=max_iterations
            )
        else:
            t = threading.Thread(
                target=AgentOptimizer._execute_workflow,
                args=(run_id, experiment_id, dataset_id, baseline_prompt_id, objective, max_iterations),
                daemon=True
            )
            t.start()
            AgentOptimizer.active_threads[run_id] = t

        return run_id

    @staticmethod
    def _execute_workflow(
        run_id: str,
        experiment_id: str,
        dataset_id: str,
        baseline_prompt_id: str,
        objective: str,
        max_iterations: int
    ):
        seen_prompt_hashes = set()

        def log_tool(tool_name: str, inp: dict, out: dict, exec_ms: float, iteration: int):
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO agent_tool_logs (
                        id, agent_run_id, iteration_num, tool_name,
                        input_payload_json, output_payload_json,
                        execution_time_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"log-{uuid.uuid4().hex[:10]}",
                    run_id,
                    iteration,
                    tool_name,
                    json.dumps(inp),
                    json.dumps(out),
                    exec_ms,
                    datetime.now(timezone.utc).isoformat()
                ))

        try:
            # 1. Step: Run baseline evaluation on TUNING split
            t0 = time.perf_counter()
            baseline_eval = AgentTools.evaluate_prompt(
                prompt_id=baseline_prompt_id,
                dataset_id=dataset_id,
                split="train",
                experiment_id=experiment_id
            )
            eval_ms = round((time.perf_counter() - t0) * 1000, 2)
            log_tool("evaluate_prompt", {"prompt_id": baseline_prompt_id, "split": "train"}, {"eval_id": baseline_eval["id"], "acc": baseline_eval["accuracy"]}, eval_ms, 0)

            # Record baseline evaluation in agent run
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE agent_runs 
                    SET baseline_eval_id = ?, best_prompt_id = ?
                    WHERE id = ?
                """, (baseline_eval["id"], baseline_prompt_id, run_id))

            # Retrieve prompt hash to prevent duplicate candidates
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT content_hash FROM prompts WHERE id = ?", (baseline_prompt_id,))
                p_hash = cursor.fetchone()["content_hash"]
                seen_prompt_hashes.add(p_hash)

            current_best_prompt_id = baseline_prompt_id
            current_best_eval_id = baseline_eval["id"]
            current_best_metrics = {
                "accuracy": baseline_eval["accuracy"],
                "f1": baseline_eval["macro_f1"],
                "invalid_outputs": baseline_eval["invalid_outputs"],
                "avg_latency_ms": baseline_eval["avg_latency_ms"]
            }

            stop_reason = "Max iterations completed"

            # 2. Iterative Optimization Loop
            for iter_num in range(1, max_iterations + 1):
                # Update current iteration in agent run
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE agent_runs SET current_iteration = ? WHERE id = ?", (iter_num, run_id))

                # Step: Inspect failures on current best
                t0 = time.perf_counter()
                failure_report = AgentTools.inspect_failures(current_best_eval_id)
                inspect_ms = round((time.perf_counter() - t0) * 1000, 2)
                log_tool("inspect_failures", {"eval_id": current_best_eval_id}, {"failures": failure_report["total_failures"], "patterns_count": len(failure_report["patterns"])}, inspect_ms, iter_num)

                # Check stopping condition: 100% accuracy and zero invalid outputs
                if failure_report["total_failures"] == 0:
                    stop_reason = "Optimal performance reached: 100% accuracy and zero invalid outputs."
                    break

                # Step: Select strategy based on highest frequency failure pattern
                patterns = failure_report.get("patterns", [])
                if patterns:
                    top_pattern = patterns[0]
                    strategy = top_pattern["recommended_strategy"]
                    failure_summary = f"{top_pattern['category']}: {top_pattern['hypothesis']}. Example failed input: {top_pattern['examples'][0]['input_text']}"
                else:
                    strategy = "instruction_clarity"
                    failure_summary = "General boundary errors observed."

                # Step: Generate candidate prompt
                t0 = time.perf_counter()
                candidate_prompt = AgentTools.generate_candidate(
                    current_prompt_id=current_best_prompt_id,
                    strategy=strategy,
                    failure_summary=failure_summary,
                    experiment_id=experiment_id
                )
                gen_ms = round((time.perf_counter() - t0) * 1000, 2)
                log_tool("generate_candidate", {"strategy": strategy, "parent": current_best_prompt_id}, {"cand_id": candidate_prompt["id"], "hash": candidate_prompt["content_hash"]}, gen_ms, iter_num)

                # Cycle / duplicate check
                if candidate_prompt["content_hash"] in seen_prompt_hashes:
                    stop_reason = f"Cycle detected: Candidate prompt at iteration {iter_num} has identical content hash to previous candidate."
                    break
                seen_prompt_hashes.add(candidate_prompt["content_hash"])

                # Step: Evaluate candidate on EXACT SAME tuning dataset split
                t0 = time.perf_counter()
                cand_eval = AgentTools.evaluate_prompt(
                    prompt_id=candidate_prompt["id"],
                    dataset_id=dataset_id,
                    split="train",
                    experiment_id=experiment_id
                )
                cand_eval_ms = round((time.perf_counter() - t0) * 1000, 2)
                log_tool("evaluate_prompt", {"prompt_id": candidate_prompt["id"], "split": "train"}, {"eval_id": cand_eval["id"], "acc": cand_eval["accuracy"]}, cand_eval_ms, iter_num)

                # Step: Compare candidate with current best using objective
                t0 = time.perf_counter()
                comparison = AgentTools.compare_candidates(
                    baseline_eval_id=current_best_eval_id,
                    candidate_eval_id=cand_eval["id"],
                    objective=objective
                )
                comp_ms = round((time.perf_counter() - t0) * 1000, 2)
                log_tool("compare_candidates", {"best": current_best_eval_id, "cand": cand_eval["id"], "objective": objective}, {"decision": comparison["decision"]}, comp_ms, iter_num)

                decision = comparison["decision"]
                rationale = comparison["rationale"]

                metrics_snapshot = {
                    "accuracy": cand_eval["accuracy"],
                    "f1": cand_eval["macro_f1"],
                    "invalid_outputs": cand_eval["invalid_outputs"],
                    "avg_latency_ms": cand_eval["avg_latency_ms"],
                    "acc_diff": comparison["accuracy_diff"],
                    "latency_diff_ms": comparison["latency_diff_ms"]
                }

                # Record iteration
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO agent_iterations (
                            id, agent_run_id, iteration_num, strategy_chosen,
                            candidate_prompt_id, candidate_eval_id, decision,
                            decision_rationale, metrics_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"iter-{uuid.uuid4().hex[:10]}",
                        run_id,
                        iter_num,
                        strategy,
                        candidate_prompt["id"],
                        cand_eval["id"],
                        decision,
                        rationale,
                        json.dumps(metrics_snapshot),
                        datetime.now(timezone.utc).isoformat()
                    ))

                # Update best if accepted
                if decision == "accepted":
                    current_best_prompt_id = candidate_prompt["id"]
                    current_best_eval_id = cand_eval["id"]
                    current_best_metrics = metrics_snapshot

                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE agent_runs SET best_prompt_id = ? WHERE id = ?", (current_best_prompt_id, run_id))
                        # Update prompt best flag
                        cursor.execute("UPDATE prompts SET is_best = 0 WHERE experiment_id = ?", (experiment_id,))
                        cursor.execute("UPDATE prompts SET is_best = 1 WHERE id = ?", (current_best_prompt_id,))

            # 3. Final Step: Run held-out evaluation on the TEST split ONLY on the final selected prompt
            t0 = time.perf_counter()
            heldout_eval = AgentTools.evaluate_prompt(
                prompt_id=current_best_prompt_id,
                dataset_id=dataset_id,
                split="test",
                experiment_id=experiment_id
            )
            heldout_ms = round((time.perf_counter() - t0) * 1000, 2)
            log_tool("evaluate_prompt (held-out)", {"prompt_id": current_best_prompt_id, "split": "test"}, {"eval_id": heldout_eval["id"], "acc": heldout_eval["accuracy"]}, heldout_ms, max_iterations + 1)

            # Finalize agent run record
            final_failures = AgentTools.inspect_failures(current_best_eval_id)
            done_time = datetime.now(timezone.utc).isoformat()

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE agent_runs SET
                        status = 'completed',
                        best_prompt_id = ?,
                        final_heldout_eval_id = ?,
                        stop_reason = ?,
                        failure_analysis_json = ?,
                        completed_at = ?
                    WHERE id = ?
                """, (
                    current_best_prompt_id,
                    heldout_eval["id"],
                    stop_reason,
                    json.dumps(final_failures),
                    done_time,
                    run_id
                ))

        except Exception as err:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE agent_runs SET
                        status = 'failed',
                        stop_reason = ?,
                        completed_at = ?
                    WHERE id = ?
                """, (
                    f"Agent execution error: {str(err)}",
                    datetime.now(timezone.utc).isoformat(),
                    run_id
                ))

    @staticmethod
    def get_run(run_id: str) -> dict | None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,))
            r = cursor.fetchone()
            if not r:
                return None

            cursor.execute("""
                SELECT ai.*, p.name as candidate_prompt_name 
                FROM agent_iterations ai
                JOIN prompts p ON ai.candidate_prompt_id = p.id
                WHERE ai.agent_run_id = ?
                ORDER BY ai.iteration_num ASC
            """, (run_id,))
            iter_rows = cursor.fetchall()
            iterations = [
                {
                    "id": i["id"],
                    "iteration_num": i["iteration_num"],
                    "strategy_chosen": i["strategy_chosen"],
                    "candidate_prompt_id": i["candidate_prompt_id"],
                    "candidate_prompt_name": i["candidate_prompt_name"],
                    "candidate_eval_id": i["candidate_eval_id"],
                    "decision": i["decision"],
                    "decision_rationale": i["decision_rationale"],
                    "metrics": json.loads(i["metrics_json"] or "{}"),
                    "created_at": i["created_at"]
                }
                for i in iter_rows
            ]

            cursor.execute("""
                SELECT * FROM agent_tool_logs 
                WHERE agent_run_id = ? 
                ORDER BY id ASC
            """, (run_id,))
            tool_rows = cursor.fetchall()
            tool_logs = [
                {
                    "id": t["id"],
                    "iteration_num": t["iteration_num"],
                    "tool_name": t["tool_name"],
                    "input_payload": json.loads(t["input_payload_json"] or "{}"),
                    "output_payload": json.loads(t["output_payload_json"] or "{}"),
                    "execution_time_ms": t["execution_time_ms"],
                    "created_at": t["created_at"]
                }
                for t in tool_rows
            ]

            return {
                "id": r["id"],
                "experiment_id": r["experiment_id"],
                "dataset_id": r["dataset_id"],
                "baseline_prompt_id": r["baseline_prompt_id"],
                "best_prompt_id": r["best_prompt_id"],
                "baseline_eval_id": r["baseline_eval_id"],
                "final_heldout_eval_id": r["final_heldout_eval_id"],
                "status": r["status"],
                "objective": r["objective"],
                "max_iterations": r["max_iterations"],
                "current_iteration": r["current_iteration"],
                "stop_reason": r["stop_reason"],
                "failure_analysis": json.loads(r["failure_analysis_json"] or "{}"),
                "created_at": r["created_at"],
                "completed_at": r["completed_at"],
                "iterations": iterations,
                "tool_logs": tool_logs
            }

    @staticmethod
    def list_runs(experiment_id: str = None) -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM agent_runs"
            params = []
            if experiment_id:
                query += " WHERE experiment_id = ?"
                params.append(experiment_id)
            query += " ORDER BY created_at DESC LIMIT 50"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "experiment_id": r["experiment_id"],
                    "dataset_id": r["dataset_id"],
                    "baseline_prompt_id": r["baseline_prompt_id"],
                    "best_prompt_id": r["best_prompt_id"],
                    "baseline_eval_id": r["baseline_eval_id"],
                    "final_heldout_eval_id": r["final_heldout_eval_id"],
                    "status": r["status"],
                    "objective": r["objective"],
                    "max_iterations": r["max_iterations"],
                    "current_iteration": r["current_iteration"],
                    "stop_reason": r["stop_reason"],
                    "failure_analysis": json.loads(r["failure_analysis_json"] or "{}"),
                    "created_at": r["created_at"],
                    "completed_at": r["completed_at"]
                }
                for r in rows
            ]
