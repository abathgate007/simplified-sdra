# Author: Andrew Bathgate | Date: 2025-06-26
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass
class Config:
    openai_api_key: str
    anthropic_api_key: str = None
    google_api_key: str = None
    deepseek_api_key: str = None
    groq_api_key: str = None

def load_config() -> Config:
    config = Config(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )

    print_config_summary(config)

    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required but not set.")

    return config

def print_config_summary(config: Config):
    def key_summary(name, value, prefix_len=6):
        if value:
            print(f"✅ {name} exists: {value[:prefix_len]}...")
        else:
            print(f"⚠️  {name} not set")

    print("\n🔐 Loaded API Keys:")
    key_summary("OPENAI_API_KEY", config.openai_api_key)
    key_summary("ANTHROPIC_API_KEY", config.anthropic_api_key)
    key_summary("GOOGLE_API_KEY", config.google_api_key, prefix_len=2)
    key_summary("DEEPSEEK_API_KEY", config.deepseek_api_key, prefix_len=3)
    key_summary("GROQ_API_KEY", config.groq_api_key, prefix_len=4)