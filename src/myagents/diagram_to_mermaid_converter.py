import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from openai import OpenAI

@dataclass
class DiagramToMermaidConverter:
    model_name: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    client: Optional[OpenAI] = None

    def __post_init__(self):
        if not self.client:
            if not self.api_key:
                raise ValueError("OpenAI API key must be provided")
            self.client = OpenAI(api_key=self.api_key)

    def convert(self, image_path: str | Path, output_path: str | Path | None = None,
                extra_instructions: str = "") -> str:
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(p)
        b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        messages = [
            {"role": "system", "content":
             "Convert architecture diagrams to VALID Mermaid only (no backticks/no prose). "
             "Choose one type: flowchart TD | sequenceDiagram | classDiagram | erDiagram. "
             "Preserve labels; concise IDs; include all edges."},
            {"role": "user", "content": [
                {"type": "text", "text": "Convert this diagram to Mermaid. " + extra_instructions},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]},
        ]
        resp = self.client.chat.completions.create(model=self.model_name, messages=messages, temperature=1)
        mermaid = self._extract_mermaid(resp.choices[0].message.content or "")
        if output_path and mermaid:
            Path(output_path).write_text(mermaid, encoding="utf-8")
        return mermaid

    @staticmethod
    def _extract_mermaid(text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            t = t.split("```", 1)[1]
            t = t.lstrip("mermaid").lstrip()
            if "```" in t:
                t = t.rsplit("```", 1)[0].strip()
        return t
