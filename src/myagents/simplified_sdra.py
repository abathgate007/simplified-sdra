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
    args = ap.parse_args()

    agent = SimplifiedSecurityDesignReviewAgent()
    if args.parse:
        text = agent.parse_design_folder(args.parse)
        print(text[:1200])  # preview
    else:
        agent.run_once()
