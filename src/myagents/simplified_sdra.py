# src/myagents/simplified_sdra.py
from dataclasses import dataclass
import asyncio
from typing import Optional

from .config import load_config, Config
from .llm_model import LLMModel

from .document_parser import DocumentParser
from .diagram_to_mermaid_converter import DiagramToMermaidConverter

from pathlib import Path
from datetime import datetime

# New: simple, hard-coded review prompt template. This will not be used in final product ---
REVIEW_SYSTEM_PROMPT = (
    "You are a senior application security architect. "
    "Given a software design, produce a short security design review. "
    "Focus on key risks (STRIDE/OWASP where relevant), trust boundaries, and prioritized mitigations. "
    "Keep it concise and actionable."
)
REVIEW_USER_PREFIX = (
    "Here is the design to review. "
    "Summarize the design’s security posture, list the top 5 risks with rationale, and provide prioritized mitigations.\n"
    "=== DESIGN START ===\n"
)

@dataclass
class SimplifiedSecurityDesignReviewAgent:
    config: Config

    def __init__(self, config_source: Optional[str] = None):
        self.config = load_config()
        print("✅ SimplifiedSecurityDesignReviewAgent initialized: config validated.")

    def parse_design_folder(self, folder: str | None = None) -> str:
        conv = DiagramToMermaidConverter(api_key=self.config.openai_api_key, model_name="gpt-4o-mini")
        dp = DocumentParser(converter=conv)
        if folder is None:
            raise ValueError("Provide a folder path (keep this simple in the new repo).")
        dp.parse_folder(folder)
        return dp.get_design_as_text()

    # --- New: async review given raw design text (single-model, simple call) ---
    async def review_design_async(self, design_text: str, model_name: str = "gpt-4o-mini") -> str:
        if not design_text or not design_text.strip():
            raise ValueError("design_text is empty")

        model = LLMModel(
            model_name=model_name,
            api_key=self.config.openai_api_key,
            model_type="openai",
        )
        print(f"🔎 Reviewing with model={model.model_name}, key={model.short_id()}")

        # For now, we just concatenate a system-ish instruction + user content.
        # If your LLMModel supports explicit system/user roles, you can adapt.
        prompt = f"{REVIEW_SYSTEM_PROMPT}\n\n{REVIEW_USER_PREFIX}{design_text}\n=== DESIGN END ==="
        response = await model.call(prompt)
        return response

    # --- New: sync helper: parse a folder then review it ---
    def review_folder_once(self, folder: str, model_name: str = "gpt-4o-mini") -> str:
        design_text = self.parse_design_folder(folder)
        return asyncio.run(self.review_design_async(design_text, model_name=model_name))

    async def test_llm(self) -> None:
        model = LLMModel(model_name="gpt-4o-mini",
                         api_key=self.config.openai_api_key,
                         model_type="openai")
        print(f"🤖 Using model={model.model_name}, key={model.short_id()}")
        resp = await model.call("Tell me a short, funny joke about security reviews.")
        print("\n🃏 Model response:\n", resp)

    def run_once(self) -> None:
        print("🧪 run_once(): calling model for a joke...")
        asyncio.run(self.test_llm())



if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--parse", type=str, help="Folder of design docs to parse")
    ap.add_argument("--review", type=str, help="Folder of design docs to parse and review")
    ap.add_argument("--model", type=str, default="gpt-4o-mini", help="LLM model name (default: gpt-4o-mini)")
    args = ap.parse_args()

    agent = SimplifiedSecurityDesignReviewAgent()
    if args.review:
        out = agent.review_folder_once(args.review, model_name=args.model)
        print(out)
    elif args.parse:
        text = agent.parse_design_folder(args.parse)
        print(text[:1200])  # preview
    else:
        agent.run_once()
