from app.database import get_db

class FailureAnalysisService:
    @staticmethod
    def analyze_evaluation(evaluation_id: str) -> dict:
        """
        Analyze failures for a given evaluation and generate evidence-based actionable hypotheses.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM evaluation_results 
                WHERE evaluation_id = ? AND is_correct = 0
            """, (evaluation_id,))
            failures = cursor.fetchall()

            cursor.execute("SELECT total_examples FROM evaluations WHERE id = ?", (evaluation_id,))
            eval_row = cursor.fetchone()
            total_examples = eval_row["total_examples"] if eval_row else len(failures)

        total_failures = len(failures)
        failure_rate = round(total_failures / total_examples, 4) if total_examples > 0 else 0.0

        if not failures:
            return {
                "evaluation_id": evaluation_id,
                "total_failures": 0,
                "failure_rate": 0.0,
                "patterns": []
            }

        # Categorize failures by inspecting types and text patterns
        invalid_format_exs = []
        negation_exs = []
        sarcasm_exs = []
        mixed_sentiment_exs = []
        general_wrong_exs = []

        for f in failures:
            item = {
                "example_id": f["example_id"],
                "input_text": f["input_text"],
                "expected": f["expected_output"],
                "actual": f["raw_output"],
                "failure_type": f["failure_type"]
            }
            inp_lower = f["input_text"].lower()

            if not f["is_valid"] or f["failure_type"] in ("INVALID_LABEL", "MALFORMED_JSON", "EXCESSIVE_VERBOSITY", "AMBIGUOUS_MULTIPLE_LABELS"):
                invalid_format_exs.append(item)
            elif "not " in inp_lower or "never " in inp_lower or "wouldn't" in inp_lower or "n't " in inp_lower:
                negation_exs.append(item)
            elif any(w in inp_lower for w in ["marvelous", "superb", "brilliant", "great, another", "what a joy"]):
                sarcasm_exs.append(item)
            elif " but " in inp_lower or " though " in inp_lower or "although " in inp_lower:
                mixed_sentiment_exs.append(item)
            else:
                general_wrong_exs.append(item)

        patterns = []

        if invalid_format_exs:
            patterns.append({
                "category": "Invalid Output Format & Label Drift",
                "count": len(invalid_format_exs),
                "examples": invalid_format_exs[:3],
                "hypothesis": "The model produces conversational prefixes or invalid labels due to unconstrained instructions.",
                "recommended_strategy": "enforce_exact_labels",
                "expected_metric_impact": "Hypothesis: Eliminates format errors, reducing invalid output count to zero.",
                "potential_tradeoffs": "Extremely strict format rules might suppress helpful reasoning on complex tasks."
            })

        if negation_exs:
            patterns.append({
                "category": "Negation Blindness (Double Negatives & Reversals)",
                "count": len(negation_exs),
                "examples": negation_exs[:3],
                "hypothesis": "The model associates isolated negative keywords ('bad', 'uncomfortable') with negative sentiment without parsing negation context ('not bad').",
                "recommended_strategy": "negation_handling",
                "expected_metric_impact": "Hypothesis: Resolves negation misclassifications, expected accuracy gain of +10% to +20%.",
                "potential_tradeoffs": "Adding explicit negation rules increases prompt token count slightly."
            })

        if sarcasm_exs:
            patterns.append({
                "category": "Sarcasm & Ironic Tone Misinterpretation",
                "count": len(sarcasm_exs),
                "examples": sarcasm_exs[:3],
                "hypothesis": "Surface lexical cues (e.g. 'superb', 'marvelous') deceive the model when used sarcastically to complain.",
                "recommended_strategy": "sarcasm_calibration",
                "expected_metric_impact": "Hypothesis: Corrects false-positive classifications on sarcastic reviews.",
                "potential_tradeoffs": "May make the model oversensitive to hyperbole in genuinely positive reviews."
            })

        if mixed_sentiment_exs:
            patterns.append({
                "category": "Mixed Sentiment & Clause Weighting",
                "count": len(mixed_sentiment_exs),
                "examples": mixed_sentiment_exs[:3],
                "hypothesis": "The prompt lacks guidance on whether the introductory praise or the final qualifying criticism should dictate the primary sentiment.",
                "recommended_strategy": "clause_weighting",
                "expected_metric_impact": "Hypothesis: Improves consistency on multi-clause reviews.",
                "potential_tradeoffs": "Can require few-shot examples that lengthen the prompt."
            })

        if general_wrong_exs:
            patterns.append({
                "category": "General Label Ambiguity",
                "count": len(general_wrong_exs),
                "examples": general_wrong_exs[:3],
                "hypothesis": "Ambiguity on neutral vs polarized boundary cases.",
                "recommended_strategy": "instruction_clarity",
                "expected_metric_impact": "Hypothesis: Calibrates neutral class boundary definitions.",
                "potential_tradeoffs": "Neutral class precision might trade off with positive recall."
            })

        return {
            "evaluation_id": evaluation_id,
            "total_failures": total_failures,
            "failure_rate": failure_rate,
            "patterns": patterns
        }
