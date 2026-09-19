"""IBM Bob / watsonx.ai narration provider.

Real, wired integration code -- not exercised in this build, since the
development sandbox has no network access or API key. Enable it with:

    NARRATION_PROVIDER=bob
    WATSONX_API_KEY=...
    WATSONX_PROJECT_ID=...
    WATSONX_URL=https://us-south.ml.cloud.ibm.com   # or your region

When enabled, it builds the same computed-state context the template
provider uses and asks the model to phrase it into an operator brief --
the model is never asked to compute a number, only to narrate ones already
in `context`. The verifier agent still re-checks its output exactly as it
does the template provider's.
"""

from __future__ import annotations

import os

from backend.llm.provider import (
    narrate_anomalies,
    narrate_curtailment,
    narrate_forecast,
    narrate_load_balance,
    narrate_regional_distribution,
)

SYSTEM_PROMPT = """You are a grid operations narrator. You will be given already-computed
statistics (demand forecasts, renewable anomaly episodes, a load-balancing plan, and a
curtailment minimization plan) as a structured summary. Rewrite that summary as a concise,
professional operator brief in flowing prose grouped under clear headings.

Rules:
- Never introduce a number that is not already present in the supplied summary.
- Do not perform any calculation -- only rephrase and organize what is given.
- Keep it under 400 words.
"""


class BobWatsonxProvider:
    name = "ibm-bob-watsonx"

    def __init__(self) -> None:
        self.api_key = os.environ.get("WATSONX_API_KEY")
        self.project_id = os.environ.get("WATSONX_PROJECT_ID")
        self.url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_id = os.environ.get("WATSONX_MODEL_ID", "ibm/granite-13b-instruct-v2")

    def narrate(self, context: dict) -> str:
        if not self.api_key or not self.project_id:
            raise RuntimeError(
                "BobWatsonxProvider requires WATSONX_API_KEY and WATSONX_PROJECT_ID to be set. "
                "Falling back is intentional -- see backend/llm/provider.get_provider()."
            )

        # Reuse the same deterministic summarization the template provider uses to build
        # a grounded, number-complete context block -- the model only rephrases this.
        structured_summary = "\n\n".join(
            filter(
                None,
                [
                    narrate_forecast(context.get("forecast")),
                    narrate_anomalies(context.get("anomalies", [])),
                    narrate_load_balance(context.get("load_balance")),
                    narrate_curtailment(context.get("curtailment")),
                    narrate_regional_distribution(context.get("regional_distribution")),
                ],
            )
        )

        return self._call_watsonx(structured_summary)

    def _call_watsonx(self, structured_summary: str) -> str:
        import requests  # local import: optional dependency, only needed on this path

        token = self._get_iam_token()
        response = requests.post(
            f"{self.url}/ml/v1/text/generation?version=2024-05-01",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model_id": self.model_id,
                "project_id": self.project_id,
                "input": f"{SYSTEM_PROMPT}\n\nComputed summary:\n{structured_summary}\n\nOperator brief:",
                "parameters": {"max_new_tokens": 600, "temperature": 0.2},
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["results"][0]["generated_text"].strip()

    def _get_iam_token(self) -> str:
        import requests

        response = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={"apikey": self.api_key, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["access_token"]
