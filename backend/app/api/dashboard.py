from fastapi import APIRouter
from app.database import get_db
from app.llm_client import llm_client
from app.evaluation_engine import EvaluationEngine

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats():
    model_status = llm_client.check_connection_sync()

    with get_db() as conn:
        cursor = conn.cursor()

        # Count total experiments
        cursor.execute("SELECT COUNT(*) as count FROM experiments")
        total_exp = cursor.fetchone()["count"]

        # Count total evaluations
        cursor.execute("SELECT COUNT(*) as count FROM evaluations WHERE status = 'completed'")
        total_eval = cursor.fetchone()["count"]

        # Count agent runs
        cursor.execute("SELECT COUNT(*) as count FROM agent_runs")
        total_agent = cursor.fetchone()["count"]

        # Find best performing prompt across all experiments
        cursor.execute("""
            SELECT p.name, e.accuracy, e.macro_f1, e.avg_latency_ms
            FROM evaluations e
            JOIN prompts p ON e.prompt_id = p.id
            WHERE e.status = 'completed'
            ORDER BY e.accuracy DESC, e.macro_f1 DESC, e.avg_latency_ms ASC
            LIMIT 1
        """)
        best_row = cursor.fetchone()
        best_prompt_info = dict(best_row) if best_row else None

        # Quality & Latency trends (last 10 completed evaluations)
        cursor.execute("""
            SELECT e.id, p.name as prompt_name, e.accuracy, e.macro_f1, e.avg_latency_ms, e.created_at
            FROM evaluations e
            JOIN prompts p ON e.prompt_id = p.id
            WHERE e.status = 'completed'
            ORDER BY e.created_at ASC
            LIMIT 15
        """)
        trend_rows = cursor.fetchall()
        trends = [
            {
                "id": r["id"],
                "prompt": r["prompt_name"][:20],
                "accuracy": round(r["accuracy"] * 100, 1),
                "f1": round(r["macro_f1"] * 100, 1),
                "latency_ms": r["avg_latency_ms"],
                "date": r["created_at"][11:16]
            }
            for r in trend_rows
        ]

        # Recent rejected / regressed candidate iterations from agent runs
        cursor.execute("""
            SELECT ai.strategy_chosen, ai.decision_rationale, ai.created_at, p.name as prompt_name
            FROM agent_iterations ai
            JOIN prompts p ON ai.candidate_prompt_id = p.id
            WHERE ai.decision = 'rejected'
            ORDER BY ai.created_at DESC
            LIMIT 5
        """)
        reg_rows = cursor.fetchall()
        regressions = [
            {
                "prompt_name": r["prompt_name"],
                "strategy": r["strategy_chosen"],
                "reason": r["decision_rationale"],
                "time": r["created_at"]
            }
            for r in reg_rows
        ]

    latest_evals = EvaluationEngine.list_evaluations(limit=5)

    return {
        "total_experiments": total_exp,
        "total_evaluations": total_eval,
        "total_agent_runs": total_agent,
        "best_prompt": best_prompt_info,
        "trends": trends,
        "recent_regressions": regressions,
        "latest_evaluations": latest_evals,
        "model_status": model_status
    }
