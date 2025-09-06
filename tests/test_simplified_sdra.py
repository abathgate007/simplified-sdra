import asyncio
from types import SimpleNamespace
import builtins
import pytest

# Import the class under test
from myagents.simplified_sdra import SimplifiedSecurityDesignReviewAgent

# ---------- Helpers ----------
class DummyDiagramToMermaidConverter:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

class DummyDocumentParser:
    def __init__(self, converter):
        self.converter = converter
        self._parsed_folder = None
        self._text = "DESIGN_TEXT"

    def parse_folder(self, folder: str):
        self._parsed_folder = folder

    def get_design_as_text(self) -> str:
        return self._text

class DummyLLMModel:
    def __init__(self, model_name: str, api_key: str, model_type: str):
        self.model_name = model_name
        self.api_key = api_key
        self.model_type = model_type

    def short_id(self) -> str:
        # Simulate truncation of API key for display
        return (self.api_key or "")[:4] + "..."

    async def call(self, prompt: str) -> str:
        # No external calls—pure stub
        return f"JOKE: ({prompt[:20]}...)"

# ---------- Fixtures ----------
@pytest.fixture
def stub_config():
    # Minimal config with just what simplified_sdra.py uses
    return SimpleNamespace(openai_api_key="sk-test-1234567890")

# ---------- Tests ----------

def test_init_uses_load_config(monkeypatch, capsys, stub_config):
    # Stub out load_config to return our minimal config
    import myagents.simplified_sdra as sdra_mod
    monkeypatch.setattr(sdra_mod, "load_config", lambda: stub_config)

    agent = SimplifiedSecurityDesignReviewAgent()
    assert agent.config is stub_config

    # Confirms the friendly init print happens
    out = capsys.readouterr().out
    assert "initialized: config validated" in out

def test_parse_design_folder_happy_path(monkeypatch, stub_config):
    import myagents.simplified_sdra as sdra_mod
    monkeypatch.setattr(sdra_mod, "load_config", lambda: stub_config)
    # Patch constructor targets used inside parse_design_folder
    monkeypatch.setattr(sdra_mod, "DiagramToMermaidConverter", DummyDiagramToMermaidConverter)
    monkeypatch.setattr(sdra_mod, "DocumentParser", DummyDocumentParser)

    agent = SimplifiedSecurityDesignReviewAgent()
    text = agent.parse_design_folder("path/to/design")
    assert text == "DESIGN_TEXT"  # from DummyDocumentParser

def test_parse_design_folder_requires_folder(monkeypatch, stub_config):
    import myagents.simplified_sdra as sdra_mod
    monkeypatch.setattr(sdra_mod, "load_config", lambda: stub_config)
    monkeypatch.setattr(sdra_mod, "DiagramToMermaidConverter", DummyDiagramToMermaidConverter)
    monkeypatch.setattr(sdra_mod, "DocumentParser", DummyDocumentParser)

    agent = SimplifiedSecurityDesignReviewAgent()
    with pytest.raises(ValueError):
        agent.parse_design_folder(None)

@pytest.mark.asyncio
async def test_test_llm_async_prints_and_calls_model(monkeypatch, capsys, stub_config):
    import myagents.simplified_sdra as sdra_mod
    monkeypatch.setattr(sdra_mod, "load_config", lambda: stub_config)
    monkeypatch.setattr(sdra_mod, "LLMModel", DummyLLMModel)

    agent = SimplifiedSecurityDesignReviewAgent()
    await agent.test_llm()  # runs our stub model

    out = capsys.readouterr().out
    # Verifies both the model selection line and the response print
    assert "Using model=gpt-4o-mini" in out
    assert "🃏 Model response:" in out
    assert "JOKE:" in out

# In tests/test_simplified_sdra.py inside test_run_once_invokes_async_entrypoint
def test_run_once_invokes_async_entrypoint(monkeypatch, capsys, stub_config):
    import asyncio
    import myagents.simplified_sdra as sdra_mod
    monkeypatch.setattr(sdra_mod, "load_config", lambda: stub_config)

    called = {"ran": False}
    async def fake_test_llm(self):
        called["ran"] = True

    monkeypatch.setattr(
        sdra_mod.SimplifiedSecurityDesignReviewAgent,
        "test_llm",
        fake_test_llm,
    )

    # Replace asyncio.run without using get_event_loop()
    real_asyncio_run = asyncio.run
    def fake_run(coro):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    monkeypatch.setattr(asyncio, "run", fake_run)

    try:
        agent = sdra_mod.SimplifiedSecurityDesignReviewAgent()
        agent.run_once()
        assert called["ran"] is True
        out = capsys.readouterr().out
        assert "run_once(): calling model for a joke" in out
    finally:
        monkeypatch.setattr(asyncio, "run", real_asyncio_run)
