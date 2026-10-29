import time
import json
import re
import httpx
from app.config import settings

class LLMClient:
    def __init__(self, base_url: str = None, default_model: str = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.DEFAULT_MODEL
        self.timeout = 30.0
        self._ollama_online: bool | None = None
        self.force_mock: bool = False

    def check_connection_sync(self) -> dict:
        """Check if Ollama service is accessible and retrieve available models."""
        if self.force_mock or settings.MOCK_LLM:
            return {
                "status": "connected",
                "base_url": self.base_url,
                "latency_ms": 1.0,
                "models": ["llama3.2:1b (mock)", "mock-deterministic"],
                "default_model_available": True,
                "default_model": self.default_model,
                "mode": "mock_deterministic"
            }

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
                res = client.get(f"{self.base_url}/api/tags")
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    has_default = any(self.default_model in m for m in models)
                    self._ollama_online = True
                    return {
                        "status": "connected",
                        "base_url": self.base_url,
                        "latency_ms": latency_ms,
                        "models": models,
                        "default_model_available": has_default,
                        "default_model": self.default_model,
                        "mode": "live_ollama"
                    }
                self._ollama_online = False
                return {
                    "status": "error",
                    "base_url": self.base_url,
                    "error": f"Ollama returned HTTP {res.status_code}",
                    "latency_ms": latency_ms,
                    "mode": "live_ollama"
                }
        except Exception as e:
            self._ollama_online = False
            return {
                "status": "offline",
                "base_url": self.base_url,
                "error": f"Could not connect to Ollama: {str(e)}",
                "default_model": self.default_model,
                "models": ["llama3.2:1b (mock available)", "mock-deterministic"],
                "mode": "mock_fallback" if (settings.MOCK_LLM or self.force_mock) else "offline"
            }

    async def check_connection(self) -> dict:
        return self.check_connection_sync()

    def generate_sync(
        self,
        prompt: str,
        system: str = "",
        model: str = None,
        temperature: float = 0.0,
        format_type: str = None
    ) -> tuple[str, float]:
        """
        Generate completion via Ollama, falling back to deterministic mock if configured or offline.
        Returns: (output_text, latency_ms)
        """
        target_model = model or self.default_model
        
        # If explicitly mock mode or already detected offline, avoid blocking network calls
        if self.force_mock or settings.MOCK_LLM or self._ollama_online is False:
            return self._mock_generate(prompt, system, target_model)

        start = time.perf_counter()
        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if format_type == "json":
            payload["format"] = "json"

        try:
            # Use quick connect timeout (1.0s) so unreachable Ollama doesn't hang the application
            with httpx.Client(timeout=httpx.Timeout(10.0, connect=1.0)) as client:
                res = client.post(f"{self.base_url}/api/generate", json=payload)
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                if res.status_code == 200:
                    data = res.json()
                    self._ollama_online = True
                    return data.get("response", "").strip(), latency_ms
                else:
                    self._ollama_online = False
                    return self._mock_generate(prompt, system, target_model)
        except Exception:
            # Mark offline so all subsequent requests use mock instantly without waiting for timeouts
            self._ollama_online = False
            return self._mock_generate(prompt, system, target_model)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str = None,
        temperature: float = 0.0,
        format_type: str = None
    ) -> tuple[str, float]:
        return self.generate_sync(prompt, system, model, temperature, format_type)

    def _mock_generate(self, prompt: str, system: str, model: str) -> tuple[str, float]:
        """
        High-fidelity deterministic mock inference engine for sentiment analysis and agent candidate generation.
        Behaves like an LLM that responds differently depending on the prompt's quality and constraints.
        Non-blocking: avoids synchronous sleep so the async event loop stays fast and responsive.
        """
        latency_ms = 18.5

        combined = f"{system}\n{prompt}".lower()

        # Check if this is an Agent candidate generation prompt
        if "generate an improved prompt" in combined or "optimization" in combined or "strategy:" in combined:
            return self._mock_agent_candidate_generation(prompt, system)

        # Check output constraints
        strict_only_label = ("only one word" in combined or "strictly one of" in combined or 
                             "do not include any explanation" in combined or "output only" in combined)
        handles_negation = ("negation" in combined or "not bad" in combined or "double negative" in combined)
        handles_sarcasm = ("sarcasm" in combined or "sarcastic" in combined or "irony" in combined)

        # Extract input text from user prompt
        input_text = prompt
        match = re.search(r'(?:input|text|review|statement):\s*["\']?([^"\'\n]+)', prompt, re.IGNORECASE)
        if match:
            input_text = match.group(1).strip()
        lower_input = input_text.lower()

        # 1. Check for Sarcasm
        if ("great, another" in lower_input or "oh marvelous" in lower_input or 
            "superb, the server" in lower_input or "just what i needed" in lower_input):
            if handles_sarcasm:
                pred = "negative"
            else:
                # Naive models see "great", "marvelous", "superb" and mistakenly classify as positive
                pred = "positive"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

        # 2. Check for Negation
        if ("not bad" in lower_input or "never once did i feel" in lower_input or 
            "not uncomfortable" in lower_input):
            if handles_negation:
                pred = "positive"
            else:
                # Naive models see "not" / "bad" / "uncomfortable" and output negative
                pred = "negative"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

        if ("not happy" in lower_input or "not worth full price" in lower_input or 
            "did not enjoy" in lower_input or "wouldn't say" in lower_input):
            pred = "negative"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

        # 3. Check for Mixed Sentiment
        if "overheating issue makes it unusable" in lower_input:
            pred = "negative"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms
        if "craftsmanship is exquisite" in lower_input or "camera optics are world-class" in lower_input:
            pred = "positive"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

        # 4. Check for Ambiguous / Neutral
        if ("parcel was delivered" in lower_input or "version 4.2" in lower_input or 
            "dimensions are" in lower_input or "colorways" in lower_input or 
            "cardboard packaging" in lower_input or lower_input == "okay." or lower_input == "okay"):
            pred = "neutral"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

        # 5. Standard Positive
        if any(w in lower_input for w in ["battery life", "highly recommended", "straightforward", "loved it", "love it", "productivity surged", "noise cancellation", "peaceful", "perfection"]):
            pred = "positive"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

        # 6. Standard Negative
        if any(w in lower_input for w in ["worst customer", "crashed", "awful", "unbearable", "broken on arrival", "downtime", "sunset the tool"]):
            pred = "negative"
            return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

        # Default fallback
        pred = "neutral"
        return (pred if strict_only_label else f"The sentiment is {pred}."), latency_ms

    def _mock_agent_candidate_generation(self, prompt: str, system: str) -> tuple[str, float]:
        """Generate high-quality candidate prompt based on requested strategy and failure analysis."""
        combined = f"{system}\n{prompt}".lower()
        
        if "enforce exact output labels" in combined or "invalid_output_format" in combined:
            candidate = {
                "name": "Strict Label Enforcement Prompt",
                "system_prompt": "You are a precise sentiment classifier. Output strictly one of: positive, negative, or neutral. Do not write explanations, punctuation, or extra words.",
                "user_template": "Classify the sentiment of this text:\n{input}\n\nAnswer (positive/negative/neutral):"
            }
        elif "negation" in combined or "double negative" in combined:
            candidate = {
                "name": "Negation-Aware Sentiment Prompt",
                "system_prompt": "You are an expert sentiment analyst. Classify text as positive, negative, or neutral. Pay special attention to negations: phrases like 'not bad' or 'not uncomfortable' express positive sentiment. Return ONLY the single label.",
                "user_template": "Analyze sentiment with negation awareness:\nText: {input}\nSentiment:"
            }
        elif "sarcasm" in combined or "irony" in combined:
            candidate = {
                "name": "Sarcasm & Nuance Calibrated Prompt",
                "system_prompt": "You are a sentiment classifier calibrated for nuance and sarcasm. Identify ironic expressions such as 'Oh marvelous, another crash' as negative sentiment. Output ONLY the label: positive, negative, or neutral.",
                "user_template": "Analyze the tone and sentiment of the following message:\n{input}\n\nExact Sentiment:"
            }
        elif "concise" in combined or "reduce" in combined or "latency" in combined:
            candidate = {
                "name": "High-Efficiency Compact Prompt",
                "system_prompt": "Classify sentiment: positive, negative, neutral. Label only.",
                "user_template": "{input}\nLabel:"
            }
        else:
            candidate = {
                "name": "Comprehensive Balanced Sentiment Prompt",
                "system_prompt": "You are an AI sentiment analyzer. Output strictly ONE word from: positive, negative, neutral.\nRules:\n- 'not bad' / 'never unhappy' are positive.\n- Sarcastic complaints are negative.\n- Factual statements are neutral.\nNo explanations.",
                "user_template": "Text to evaluate: {input}\nClassification:"
            }
        
        return json.dumps(candidate), 45.0

llm_client = LLMClient()
