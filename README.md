Simplified Security Design Review Agent (SDRA)

Author: Andrew Bathgate
Language: Python 3.11+
Dependency manager: uv

IDE: Cursor / VS Code

Overview

The Simplified Security Design Review Agent (SDRA) is an experimental framework for performing structured security design reviews using multiple LLMs.

The agent:

Parses requirements, design docs, and architecture diagrams

Generates trust boundaries, data flow diagrams (DFDs), and threat models

Applies STRIDE and DREAD methodologies

Produces prioritized mitigations mapped to NIST CSF

Iteratively refines results with a merge–evaluate–improve loop across multiple LLMs

Outputs JSON artifacts and a minimal HTML report for stakeholders

Workflow Pipeline

Trust Boundaries → Identify boundaries and supporting evidence

DFDs → Generate Mermaid DFDs with canonical IDs

STRIDE Matrix → Map threats to each DFD element

DREAD Ratings → Quantify risk severity with fixed rubric

Mitigations → Map to NIST CSF, rank by risk, group quick wins

Annotated DFDs → Overlay threats on diagrams

Final Deliverables → Bundle JSON artifacts + static HTML report

All steps run through the merge–evaluate–improve loop (fan-out across models → merge results → evaluator LLM → optional improvements, max 3 loops).

Installation

Clone the repo and sync dependencies with uv:
Make sure you have a .env file with your API keys: (POPULATED FROM VAULT)
e.g.
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...

Usage
To test LLM connectivity 
    uv run python -m myagents.simplified_sdra

Testing
    uv run pytest -q

Design Principles
    Model agnostic: adapters for GPT, Claude, Gemini
    JSON-first: schemas define strict outputs
    Proof-of-work: all findings cite evidence (requirement, diagram, or assumption)
    Iterative refinement: merge–evaluate–improve loop with bounded iterations
    Transparency: final artifacts + analytics manifest

Overview
    The Simplified Security Design Review Agent (SDRA) is an experimental framework for performing structured security design reviews using multiple LLMs.

The agent:
    Parses requirements, design docs, and architecture diagrams
    Generates trust boundaries, data flow diagrams (DFDs), and threat models
    Applies STRIDE and DREAD methodologies
    Produces prioritized mitigations mapped to NIST CSF
    Iteratively refines results with a merge–evaluate–improve loop across multiple LLMs
    Outputs JSON artifacts and a minimal HTML report for stakeholders

Workflow Pipeline
1. Trust Boundaries → Identify boundaries and supporting evidence
2. DFDs → Generate Mermaid DFDs with canonical IDs
3. STRIDE Matrix → Map threats to each DFD element
4. DREAD Ratings → Quantify risk severity with fixed rubric
5. Mitigations → Map to NIST CSF, rank by risk, group quick wins
6. Annotated DFDs → Overlay threats on diagrams
7. Final Deliverables → Bundle JSON artifacts + static HTML report
All steps run through the merge–evaluate–improve loop (fan-out across models → merge results → evaluator LLM → optional improvements, max 3 loops).
