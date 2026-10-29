import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from app.config import settings

def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Experiments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            task_type TEXT NOT NULL DEFAULT 'classification',
            model TEXT NOT NULL DEFAULT 'llama3.2:1b',
            objective TEXT NOT NULL DEFAULT 'maximize_accuracy',
            config_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        # Prompts table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id TEXT PRIMARY KEY,
            experiment_id TEXT,
            version_num INTEGER NOT NULL DEFAULT 1,
            name TEXT NOT NULL,
            system_prompt TEXT NOT NULL DEFAULT '',
            user_template TEXT NOT NULL DEFAULT '{input}',
            output_format TEXT NOT NULL DEFAULT 'labels',
            valid_labels_json TEXT DEFAULT '["positive", "negative", "neutral"]',
            json_schema_json TEXT DEFAULT '{}',
            content_hash TEXT NOT NULL,
            is_best INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
        )
        """)

        # Datasets table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            filename TEXT,
            content_hash TEXT NOT NULL,
            total_examples INTEGER NOT NULL DEFAULT 0,
            train_count INTEGER NOT NULL DEFAULT 0,
            test_count INTEGER NOT NULL DEFAULT 0,
            schema_info_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """)

        # Dataset examples table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dataset_examples (
            id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            split TEXT NOT NULL DEFAULT 'train',
            input_text TEXT NOT NULL,
            expected_output TEXT NOT NULL,
            extra_data_json TEXT DEFAULT '{}',
            example_index INTEGER NOT NULL,
            FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
        )
        """)

        # Evaluations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id TEXT PRIMARY KEY,
            experiment_id TEXT,
            prompt_id TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            split TEXT NOT NULL DEFAULT 'train',
            model TEXT NOT NULL,
            model_config_json TEXT DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            total_examples INTEGER NOT NULL DEFAULT 0,
            successful_examples INTEGER NOT NULL DEFAULT 0,
            failed_examples INTEGER NOT NULL DEFAULT 0,
            correct_predictions INTEGER NOT NULL DEFAULT 0,
            invalid_outputs INTEGER NOT NULL DEFAULT 0,
            accuracy REAL NOT NULL DEFAULT 0.0,
            macro_precision REAL NOT NULL DEFAULT 0.0,
            macro_recall REAL NOT NULL DEFAULT 0.0,
            macro_f1 REAL NOT NULL DEFAULT 0.0,
            avg_latency_ms REAL NOT NULL DEFAULT 0.0,
            median_latency_ms REAL NOT NULL DEFAULT 0.0,
            p95_latency_ms REAL NOT NULL DEFAULT 0.0,
            error_rate REAL NOT NULL DEFAULT 0.0,
            duration_ms REAL NOT NULL DEFAULT 0.0,
            confusion_matrix_json TEXT DEFAULT '{}',
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE SET NULL,
            FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE CASCADE,
            FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
        )
        """)

        # Example-level evaluation results table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_results (
            id TEXT PRIMARY KEY,
            evaluation_id TEXT NOT NULL,
            example_id TEXT,
            input_text TEXT NOT NULL,
            expected_output TEXT NOT NULL,
            raw_output TEXT,
            parsed_output TEXT,
            is_correct INTEGER NOT NULL DEFAULT 0,
            is_valid INTEGER NOT NULL DEFAULT 1,
            latency_ms REAL NOT NULL DEFAULT 0.0,
            error_message TEXT,
            failure_type TEXT,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations (id) ON DELETE CASCADE
        )
        """)

        # Agent runs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            baseline_prompt_id TEXT NOT NULL,
            best_prompt_id TEXT,
            baseline_eval_id TEXT,
            final_heldout_eval_id TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            objective TEXT NOT NULL DEFAULT 'maximize_accuracy',
            max_iterations INTEGER NOT NULL DEFAULT 3,
            current_iteration INTEGER NOT NULL DEFAULT 0,
            stop_reason TEXT,
            failure_analysis_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE,
            FOREIGN KEY (baseline_prompt_id) REFERENCES prompts (id),
            FOREIGN KEY (best_prompt_id) REFERENCES prompts (id)
        )
        """)

        # Agent iterations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_iterations (
            id TEXT PRIMARY KEY,
            agent_run_id TEXT NOT NULL,
            iteration_num INTEGER NOT NULL,
            strategy_chosen TEXT NOT NULL,
            candidate_prompt_id TEXT NOT NULL,
            candidate_eval_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            decision_rationale TEXT NOT NULL,
            metrics_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (agent_run_id) REFERENCES agent_runs (id) ON DELETE CASCADE,
            FOREIGN KEY (candidate_prompt_id) REFERENCES prompts (id),
            FOREIGN KEY (candidate_eval_id) REFERENCES evaluations (id)
        )
        """)

        # Agent tool execution logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_tool_logs (
            id TEXT PRIMARY KEY,
            agent_run_id TEXT NOT NULL,
            iteration_num INTEGER NOT NULL,
            tool_name TEXT NOT NULL,
            input_payload_json TEXT DEFAULT '{}',
            output_payload_json TEXT DEFAULT '{}',
            execution_time_ms REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (agent_run_id) REFERENCES agent_runs (id) ON DELETE CASCADE
        )
        """)

        # Create helpful indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_exp ON prompts(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_examples_ds_split ON dataset_examples(dataset_id, split)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_exp ON evaluations(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_prompt ON evaluations(prompt_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_res_eval ON evaluation_results(evaluation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_exp ON agent_runs(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_iter_run ON agent_iterations(agent_run_id)")
