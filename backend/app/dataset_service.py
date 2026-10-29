import uuid
import hashlib
import json
import csv
import io
from pathlib import Path
from datetime import datetime, timezone
from app.database import get_db
from app.config import settings

def compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]

def ensure_starter_dataset():
    """Ensure the built-in sentiment dataset exists in database."""
    starter_file = settings.DATA_DIR / "starter_sentiment.json"
    if not starter_file.exists():
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM datasets WHERE id = 'starter-sentiment-dataset'")
        row = cursor.fetchone()
        if row:
            return

        with open(starter_file, "r", encoding="utf-8") as f:
            raw_content = f.read()
            examples = json.loads(raw_content)

        dataset_id = "starter-sentiment-dataset"
        content_hash = compute_hash(raw_content)
        now_str = datetime.now(timezone.utc).isoformat()

        train_examples = [e for e in examples if e.get("split") == "train"]
        test_examples = [e for e in examples if e.get("split") == "test"]

        schema_info = {
            "task_type": "classification",
            "categories": list(set(e.get("category", "general") for e in examples)),
            "labels": ["positive", "negative", "neutral"],
            "input_field": "input",
            "expected_field": "expected_output"
        }

        cursor.execute("""
            INSERT INTO datasets (id, name, description, filename, content_hash, total_examples, train_count, test_count, schema_info_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dataset_id,
            "Starter Sentiment Classification",
            "Curated sentiment benchmark with negation, sarcasm, mixed tones, and edge cases.",
            "starter_sentiment.json",
            content_hash,
            len(examples),
            len(train_examples),
            len(test_examples),
            json.dumps(schema_info),
            now_str
        ))

        for idx, ex in enumerate(examples):
            ex_id = f"ex-starter-{idx}"
            split = ex.get("split", "train")
            inp = ex.get("input", "")
            exp = ex.get("expected_output", "")
            extra = {"category": ex.get("category", "")}

            cursor.execute("""
                INSERT INTO dataset_examples (id, dataset_id, split, input_text, expected_output, extra_data_json, example_index)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ex_id, dataset_id, split, inp, exp, json.dumps(extra), idx))

        # Ensure a default starter experiment and baseline prompt exist
        cursor.execute("SELECT id FROM experiments WHERE id = 'exp-starter-sentiment'")
        exp_row = cursor.fetchone()
        if not exp_row:
            exp_id = "exp-starter-sentiment"
            cursor.execute("""
                INSERT INTO experiments (id, name, description, task_type, model, objective, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp_id,
                "Sentiment Classification Benchmark",
                "Benchmark and optimize prompts against 30 sentiment edge cases (negation, sarcasm, and mixed tones).",
                "sentiment_classification",
                "llama3.2:1b",
                "maximize_accuracy",
                json.dumps({"valid_labels": ["positive", "negative", "neutral"]}),
                now_str,
                now_str
            ))

            # Create Baseline Prompt (v1)
            prompt_id = "prompt-starter-baseline"
            sys_prompt = "You are a precise sentiment classifier. Output strictly one of: positive, negative, or neutral."
            usr_template = "Text: {input}\nSentiment:"
            cursor.execute("""
                INSERT INTO prompts (
                    id, experiment_id, version_num, name, system_prompt, user_template,
                    output_format, valid_labels_json, json_schema_json, content_hash,
                    is_best, author_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prompt_id,
                exp_id,
                1,
                "Baseline Sentiment Prompt (v1)",
                sys_prompt,
                usr_template,
                "labels",
                json.dumps(["positive", "negative", "neutral"]),
                "{}",
                compute_hash(f"{sys_prompt.strip()}|||{usr_template.strip()}"),
                1,
                "user",
                now_str
            ))

class DatasetService:
    @staticmethod
    def list_datasets() -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM datasets ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "filename": r["filename"],
                    "content_hash": r["content_hash"],
                    "total_examples": r["total_examples"],
                    "train_count": r["train_count"],
                    "test_count": r["test_count"],
                    "schema_info": json.loads(r["schema_info_json"] or "{}"),
                    "created_at": r["created_at"]
                }
                for r in rows
            ]

    @staticmethod
    def get_dataset(dataset_id: str) -> dict | None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "filename": r["filename"],
                "content_hash": r["content_hash"],
                "total_examples": r["total_examples"],
                "train_count": r["train_count"],
                "test_count": r["test_count"],
                "schema_info": json.loads(r["schema_info_json"] or "{}"),
                "created_at": r["created_at"]
            }

    @staticmethod
    def get_examples(dataset_id: str, split: str = None, limit: int = 100, offset: int = 0) -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM dataset_examples WHERE dataset_id = ?"
            params = [dataset_id]
            if split:
                query += " AND split = ?"
                params.append(split)
            query += " ORDER BY example_index ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "dataset_id": r["dataset_id"],
                    "split": r["split"],
                    "input_text": r["input_text"],
                    "expected_output": r["expected_output"],
                    "extra_data": json.loads(r["extra_data_json"] or "{}"),
                    "example_index": r["example_index"]
                }
                for r in rows
            ]

    @staticmethod
    def create_dataset_from_records(
        name: str,
        description: str,
        filename: str,
        records: list[dict],
        input_col: str = "input",
        expected_col: str = "expected_output",
        train_ratio: float = 0.7
    ) -> dict:
        """Parse, validate, deduplicate, and split records into dataset."""
        if not records:
            raise ValueError("Dataset cannot be empty.")

        cleaned_records = []
        seen_inputs = set()
        duplicates_count = 0
        missing_count = 0

        for idx, row in enumerate(records):
            inp = str(row.get(input_col, "")).strip()
            exp = str(row.get(expected_col, "")).strip()

            if not inp or not exp:
                missing_count += 1
                continue

            if inp in seen_inputs:
                duplicates_count += 1
                continue
            seen_inputs.add(inp)

            cleaned_records.append({
                "input": inp,
                "expected": exp,
                "extra": {k: v for k, v in row.items() if k not in (input_col, expected_col)}
            })

        if not cleaned_records:
            raise ValueError(
                f"No valid examples found after parsing. Checked columns '{input_col}' and '{expected_col}'. "
                f"Missing values: {missing_count}, Duplicates: {duplicates_count}"
            )

        dataset_id = f"ds-{uuid.uuid4().hex[:10]}"
        content_repr = json.dumps([{"i": r["input"], "e": r["expected"]} for r in cleaned_records], sort_keys=True)
        content_hash = compute_hash(content_repr)
        now_str = datetime.now(timezone.utc).isoformat()

        # Deterministic 70/30 or custom split
        total = len(cleaned_records)
        train_cutoff = int(total * train_ratio)
        if train_cutoff == 0 and total > 1:
            train_cutoff = 1

        schema_info = {
            "input_column": input_col,
            "expected_column": expected_col,
            "duplicates_removed": duplicates_count,
            "missing_removed": missing_count,
            "train_ratio": train_ratio
        }

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO datasets (id, name, description, filename, content_hash, total_examples, train_count, test_count, schema_info_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_id,
                name,
                description,
                filename,
                content_hash,
                total,
                train_cutoff,
                total - train_cutoff,
                json.dumps(schema_info),
                now_str
            ))

            for idx, r in enumerate(cleaned_records):
                ex_id = f"ex-{dataset_id}-{idx}"
                split = "train" if idx < train_cutoff else "test"
                cursor.execute("""
                    INSERT INTO dataset_examples (id, dataset_id, split, input_text, expected_output, extra_data_json, example_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ex_id, dataset_id, split, r["input"], r["expected"], json.dumps(r["extra"]), idx))

        return DatasetService.get_dataset(dataset_id)
