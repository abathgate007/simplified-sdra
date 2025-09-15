from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

@dataclass
class LLMModel:
    model_name: str
    api_key: str
    base_url: Optional[str] = None  # base_url is optional
    model_type: str = "openai"  # One of: "openai", "deepseek", "google", "anthropic"

    def __post_init__(self):
        # Basic validation: ensure API key looks reasonable
        if not self.api_key or len(self.api_key) < 10:
            raise ValueError(f"Invalid API key for model '{self.model_name}'")
        if not self.model_name:
            raise ValueError("Model name cannot be empty")

    def short_id(self) -> str:
        """Returns the first few chars of the API key for debugging."""
        return self.api_key[:6] + "..."

    async def callwithmessages(self, messages: List[dict]) -> str:
        if self.model_type == "openai" or self.model_type == "deepseek":
            return await self._call_openai_stylewithmessages(messages)
        elif self.model_type == "google":
            return await self._call_geminiwithmessages(messages)
        elif self.model_type == "anthropic":
            return await self._call_claudewithmessages(messages)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    async def call(self, prompt: str) -> str:
        if self.model_type == "openai" or self.model_type == "deepseek":
            return await self._call_openai_style(prompt)
        elif self.model_type == "google":
            return await self._call_gemini(prompt)
        elif self.model_type == "anthropic":
            return await self._call_claude(prompt)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
     
    async def _call_openai_stylewithmessages(self, messages: List[dict]) -> str:
        # choose the right client first
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) \
            if self.base_url else AsyncOpenAI(api_key=self.api_key)

        async with client as session:
            response = await session.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )
        return response.choices[0].message.content or ""

    async def _call_openai_style(self, prompt: str) -> str:
        # pick client first (conditional expression is fine here)
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) \
            if self.base_url else AsyncOpenAI(api_key=self.api_key)

        async with client as session:
            response = await session.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
        return response.choices[0].message.content or ""

    async def _call_geminiwithmessages(self, messages: List[dict]) -> str:
        # Choose the client first
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) \
            if self.base_url else AsyncOpenAI(api_key=self.api_key)

        async with client as session:
            response = await session.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )
        return response.choices[0].message.content or ""

    async def _call_gemini(self, prompt: str) -> str:
        # choose the client first
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) \
            if self.base_url else AsyncOpenAI(api_key=self.api_key)

        async with client as session:
            response = await session.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
        return response.choices[0].message.content or ""

    async def _call_claudewithmessages(self, messages: List[Dict[str, Any]]) -> str:
        # Extract system messages (Anthropic requires top-level system param)
        system_parts = []
        new_messages = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                # Collect system text
                if isinstance(content, str):
                    system_parts.append(content)
                elif isinstance(content, list):
                    system_parts.extend(
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
            else:
                # Pass through user/assistant messages unchanged
                new_messages.append(m)

        system_text = "\n".join(p for p in system_parts if p)

        async with AsyncAnthropic(api_key=self.api_key) as client:
            response = await client.messages.create(
                model=self.model_name,
                max_tokens=20000,
                system=system_text or None,  # Top-level system field
                messages=new_messages,       # Only user/assistant
            )

        return response.content[0].text

    async def _call_claude(self, prompt: str) -> str:
        client = AsyncAnthropic(api_key=self.api_key)

        response = await client.messages.create(
            model=self.model_name,
            max_tokens=20000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text