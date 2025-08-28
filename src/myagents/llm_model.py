from dataclasses import dataclass
from typing import Optional
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

    async def call(self, prompt: str) -> str:
        if self.model_type == "openai" or self.model_type == "deepseek":
            return await self._call_openai_style(prompt)
        elif self.model_type == "google":
            return await self._call_gemini(prompt)
        elif self.model_type == "anthropic":
            return await self._call_claude(prompt)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    async def _call_openai_style(self, prompt: str) -> str:
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) if self.base_url \
            else AsyncOpenAI(api_key=self.api_key)

        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
    
    async def _call_gemini(self, prompt: str) -> str:
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) if self.base_url \
            else AsyncOpenAI(api_key=self.api_key)

        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
    
    async def _call_claude(self, prompt: str) -> str:
        client = AsyncAnthropic(api_key=self.api_key)

        response = await client.messages.create(
            model=self.model_name,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text