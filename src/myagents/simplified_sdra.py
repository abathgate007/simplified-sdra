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
from tkinter import Tk, filedialog
from typing import Optional, Tuple, Dict
from typing import List
import json
from time import perf_counter

import os, base64 #for dumping to json files

import asyncio
import openai
from openai import AsyncOpenAI


@dataclass
class SimplifiedSecurityDesignReviewAgent:
    config: Config
    requirements: Optional[str] = None       # parsed design text
    phase1_output: Optional[str] = None      # Trust Boundaries, DFDs, STRIDE
    phase2_output: Optional[str] = None      # DREAD, Annotated DFDs, Mitigations
    final_report: Optional[str] = None       # Final report text



    def build_models(self) -> list[LLMModel]:
        return [
            LLMModel(model_name="gpt-5", api_key=self.config.openai_api_key, model_type="openai"),
            LLMModel(model_name="claude-sonnet-4-20250514", api_key=self.config.anthropic_api_key, model_type="anthropic")
        ]


    def __init__(self, config_source: Optional[str] = None):
        self.config = load_config()
        self.requirements = None
        self.phase1_output = None
        self.phase2_output = None
        self.final_report = None
        print("✅ SimplifiedSecurityDesignReviewAgent initialized: config validated.")

    def load_prompt(self, filename: str, version: Optional[str] = None) -> str:
        """
        Load a prompt file from prompts/<version>/<filename> relative to the project root.
        Always reads fresh from disk. No caching.
        """
        v = version or "v1"
        project_root = Path(__file__).resolve().parents[2]
        prompt_path = project_root / "prompts" / v / filename

        print(f"📄 Loading prompt: {prompt_path}")
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        return prompt_path.read_text(encoding="utf-8")

    def prompt_for_design_folder(self) -> str:
        """
        Open a file dialog to let the user pick the folder that contains
        the requirements and design documents. Returns the selected path.
        """
        # Hide the root Tk window
        root = Tk()
        root.withdraw()

        folder = filedialog.askdirectory(title="Select requirements/design folder")
        root.destroy()

        if not folder:
            raise ValueError("No folder selected.")
        return folder

    def parse_design_folder(self, folder: str | None = None) -> str:
        conv = DiagramToMermaidConverter(api_key=self.config.openai_api_key, model_name="gpt-5")
        dp = DocumentParser(converter=conv)
        if folder is None:
            raise ValueError("Provide a folder path (keep this simple in the new repo).")
        dp.parse_folder(folder)
        self.requirements = dp.get_design_as_text()
        
        # Save requirements to file
        with open('parsedrequirements.txt', 'w', encoding='utf-8') as f:
            f.write(self.requirements)
        
        return dp.get_design_as_text()


    async def eval_suggest_improve(
        self,
        system_prompt: str,
        user_prompt: str,
        models: List[LLMModel],   # <-- was List[str]
    ) -> str:
        """
        Prepare role-based messages, call the models up to 3 rounds,
        merge their outputs, ask for suggested improvements, and stop
        early if no suggestions are returned. Returns the final merged output.
        """
        if not self.requirements:
            raise ValueError("Requirements not set. Parse the design folder before evaluation.")

        # Prepare role-based messages (user prompt should already include any placeholders filled in)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        merged_output: str = ""
        for round_idx in range(1, 3):  # up to 2 iterations
            print(f"🔁 evalSuggestImprove: round {round_idx}")

            # Call all models asynchronously with the same messages
            outputs = await self.call_models(messages, models)

            merged_output = await self.merge_outputs(outputs)

            
            # Evaluate merged output and ask for suggestions (stub logic for now)
            suggested = await self.evaluate_merged_output(merged_output)

            if isinstance(suggested, str) and suggested.strip().lower() == "none":
                print("✅ No further improvements suggested. Stopping.")
                break

            # If suggestions exist, append them to the user prompt to guide the next round
            if suggested:
                # Simple pattern: feed suggestions back into the next user turn
                improved_user = (
                    user_prompt
                    + "\n\n---\nPlease incorporate the following improvement suggestions:\n"
                    + str(suggested)
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": improved_user},
                ]

        return merged_output


    # --- accept List[LLMModel] and use each instance directly ---
    async def call_models(self, messages: List[dict], models: List[LLMModel]) -> List[str]:
        """
        Asynchronously call each model with the same prompts.
        Collect all outputs into a list and return.
        """
        if not models:
            raise ValueError("No models provided to call_models().")

        async def _call_one(model: LLMModel) -> str:
            # SAFE logging: do not print the whole dataclass (it includes the API key)
            try:
                print(f"🤖 Calling {model.model_name} key={model.short_id()}")
            except Exception:
                print("🤖 Calling model (short_id unavailable)")
            start_time = perf_counter()
            try:
                return await model.callwithmessages(messages)
            except Exception as e:
                # Log the model name only (avoid leaking api_key via dataclass repr)
                return f"[ERROR from {model.model_name}] {e.__class__.__name__}: {e}"
            finally:
                end_time = perf_counter()
                print(f"🤖 {model.model_name} took {end_time - start_time:.2f} seconds")

        tasks = [_call_one(m) for m in models] #Creates a list of coroutines
        return await asyncio.gather(*tasks) #Waits for all coroutines to complete and returns a list of results


    async def merge_outputs(self, outputs: List[str]) -> str:
        """
        Merge multiple model outputs that share the same JSON schema into a single
        superset without duplicates.  Returns a JSON string.

        Contract:
        - Each element in `outputs` should be a JSON string with the SAME top-level schema.
        - This method returns a SINGLE JSON string with the same schema, combining all
            entries across inputs and removing duplicates (semantic duplicates OK).
        """
        if not outputs:
            return "{}"

        system_prompt = (
            "You are a senior data engineer. You will receive multiple JSON documents "
            "that are intended to share the SAME top-level schema (e.g., { trust_boundaries, dfds, stride, ... } "
            "or any analogous structure). Merge them into a SINGLE JSON with the SAME schema that is a superset "
            "of all unique entries across inputs. Remove duplicates (including semantic duplicates). "
            "Rules:\n"
            "1) Keep the same keys and nesting as the inputs.\n"
            "2) For array fields, produce the union with deduplication. Prefer richer/longer entries on conflict.\n"
            "3) For object fields with identical keys, prefer the most complete (non-null, longer) value.\n"
            "4) Ensure STRICT JSON output ONLY — no markdown, no commentary.\n"
            "5) If any input is malformed JSON, do your best to infer and integrate the content correctly.\n"
            "6) Preserve stable IDs if present; otherwise dedupe by normalized title/name + content similarity.\n"
            "7) Do not invent fields not present in the inputs.\n"
        )

        # To keep your current LLMModel.call API (string prompt), we flatten into a single prompt string.
        # If you already support role-based messages in LLMModel.call, you can switch to that easily.
        prompt_parts = [
            "You will merge the following JSON payloads.\n",
            "=== WELL-FORMED JSON PAYLOADS ==="
        ]
        for i, p in enumerate(outputs, start=1):
            prompt_parts.append(f"\n-- JSON #{i} --\n{json.dumps(p, ensure_ascii=False)}")

        prompt_parts.append("\n\nReturn STRICT JSON only.")
        combined_user_prompt = "\n".join(prompt_parts)
        
        # Save combined_user_prompt to file
        with open('combined_user_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(combined_user_prompt)
        

        # 3) Call GPT-5 to produce the merged superset JSON.
        try:
            gpt5 = LLMModel(
                model_name="gpt-5",
                api_key=self.config.openai_api_key,
                model_type="openai",
            )

            messages = [
               {"role": "system", "content": system_prompt},
               {"role": "user", "content": combined_user_prompt},
            ]
            resp = await gpt5.callwithmessages(messages)
            return resp

        except Exception as e:
            print(f"⚠️ GPT-5 merge failed. Reason: {e}")
        return "{FAILED TO MERGE}"


    async def evaluate_merged_output(self, merged_output: str):
        """
        Evaluate the merged Phase 1 output (Trust Boundaries, DFDs, STRIDE)
        against self.requirements for completeness, lack of duplication, and
        meaningful STRIDE entries. Uses GPT-5 and returns either:
        - a JSON string (list of suggested improvements), or
        - the string "None" if no improvements are needed.
        """
        if not self.requirements:
            raise ValueError("Requirements not set. Parse the design folder before evaluation.")
        if not merged_output or not merged_output.strip():
            raise ValueError("Merged output is empty.")

        # System prompt: strict JSON, schema + rules
        system_prompt = """
        You are a senior application security reviewer.
        TASK: Evaluate MERGED_PHASE1_OUTPUT for COMPLETENESS and QUALITY...

        OUTPUT FORMAT (STRICT JSON ONLY — no markdown, no commentary):
        EITHER: the string literal "None"
        OR: a JSON array of suggestion objects with this exact schema:
        [
            {
            "category": "trust_boundary" | "dfd" | "stride",
            "id_or_location": "string",
            "issue": "string",
            "rationale": "string",
            "suggested_change": "string"
            }
        ]
        """
        # User prompt includes the inputs verbatim
        user_prompt = (
            "REQUIREMENTS_AND_DESIGN_TEXT:\n"
            "------------------------------\n"
            f"{self.requirements}\n\n"
            "MERGED_PHASE1_OUTPUT (JSON):\n"
            "----------------------------\n"
            f"{merged_output}\n\n"
            "Return STRICT JSON only (either \"None\" or a JSON array following the schema)."
        )

        # Call GPT-5 (flattened to a single prompt string for current LLMModel API)
        try:
            reviewer = LLMModel(
                model_name="gpt-5",
                api_key=self.config.openai_api_key,
                model_type="openai",
            )
            prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"
            resp = (await reviewer.call(prompt)).strip()
        except Exception as e:
            print(f"evaluate_merged_output: model call failed: {e}")
            return "None"

        # Normalize/validate the response:
        # Accept exact "None" (case-sensitive as specified), or a JSON array per schema.
        if resp == "None":
            return "None"

        # If the model returned JSON, ensure it's valid; attempt gentle extraction if needed
        try:
            parsed = json.loads(resp)
            # If it's a dict that wraps suggestions, try to unwrap a common field name
            if isinstance(parsed, dict):
                for key in ("suggestions", "improvements", "items"):
                    if key in parsed and isinstance(parsed[key], list):
                        return json.dumps(parsed[key], ensure_ascii=False)
                # Unexpected object shape -> treat as no-op
                return "None"
            # If it's a list, return as-is
            if isinstance(parsed, list):
                return json.dumps(parsed, ensure_ascii=False)
            # Any other JSON type -> treat as no suggestions
            return "None"
        except Exception:
            # As a last resort, try to extract a JSON array from the text
            import re
            m = re.search(r'(\[\s*\{.*\}\s*\])', resp, flags=re.DOTALL)
            if m:
                candidate = m.group(1)
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    pass
            # If we can't validate, err on the side of not looping forever
            return "None"
            
    async def run_phase1_trust_dfd_stride(self, system_prompt: str, user_prompt: str) -> str:
        """
        Phase 1: Produce Trust Boundaries, DFDs, and STRIDE outputs.
        Inserts requirements into the user_prompt placeholder and calls the LLM.
        """
        if not self.requirements:
            raise ValueError("Requirements not set. Did you parse the design folder first?")

        print("▶️ Phase 1: Trust Boundaries, DFDs, STRIDE")

        # Replace placeholder with the requirements text
        filled_user_prompt = user_prompt.replace("<<REQUIREMENTS_AND_DESIGN_TEXT>>", self.requirements)

        models = self.build_models()
        response = await self.eval_suggest_improve(system_prompt, filled_user_prompt, models)
        
        self.phase1_output = response
        # Save phase1_output as a single string to file
        with open("firstphase_output.txt", "w", encoding="utf-8") as f:
            f.write(self.phase1_output)

        return self.phase1_output

    def run_phase2_dread_annotations_mitigations(self, system_prompt: str, user_prompt: str) -> str:
        print("▶️ Phase 2: DREAD, Annotated DFDs, Mitigations (stub)")
        self.phase2_output = "PHASE2: DREAD + Annotated DFDs + Mitigations (TBD)"
        return self.phase2_output

    async def run_phase3_final_report(self, system_prompt: str, user_prompt: str) -> str:
        """
        Phase 3: Generate the final report via GPT-5 using role-based messages.
        Assumes the provided prompts already contain Phase 1 and Phase 2 data.
        """
        print("▶️ Phase 3: Final Report")

        # Build role-based messages directly from the provided prompts
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Initialize GPT-5 model client
        gpt5 = LLMModel(
            model_name="gpt-5",
            api_key=self.config.openai_api_key,
            model_type="openai",
        )

        try:
            # Use the role-aware API
            self.final_report = await gpt5.callwithmessages(messages)
        except Exception as e:
            print(f"⚠️ Phase 3 final report generation failed: {e}")
            self.final_report = f"ERROR: {e}"

        return self.final_report
        
    async def run_multistep_review(self) -> str:
        """
        Top-level multi-step review orchestrator.
        Prompts the user for the design folder (via file dialog).
        For now, it just returns 'Done' after capturing the folder path.
        """
        folder = self.prompt_for_design_folder()
        print(f"Selected design folder: {folder}")
        self.parse_design_folder(folder) #populates self.requirements
        
        #Read requirements from file - THIS IS JUST FOR TESTING
        #with open('parsedrequirements.txt', 'r', encoding='utf-8') as f:
        #    self.requirements = f.read()
        print(f"Parsed requirements: {self.requirements[:1200]}")

        #First phase
        first_system_prompt = self.load_prompt("Trust_DFD_STRIDE_System_Prompt.txt", "v1")
        first_user_prompt = self.load_prompt("Trust_DFD_STRIDE_User_Prompt.txt", "v1")
        print(f"First system prompt: {first_system_prompt}")
        print(f"First user prompt: {first_user_prompt}")
        phase1 = await self.run_phase1_trust_dfd_stride(first_system_prompt, first_user_prompt)
        print(f"✅ Phase 1 output preview: {str(phase1)[:1400]}")
        with open("firstphase_output.txt", "w", encoding="utf-8") as f:
            f.write(phase1)

        #Read firstphase_output.txt file and assign it to phase1
        #with open("firstphase_output.txt", "r", encoding="utf-8") as f:
            #phase1 = f.read()
        
        
        #Second phase
        second_phase_system_prompt = self.load_prompt("DREAD_AnnotatedDFD_Mitigations_System_Prompt.txt", "v1")
        second_phase_user_prompt = "Context (inputs produced by earlier steps):" + phase1 + "\n\n" + self.load_prompt("DREAD_AnnotatedDFD_Mitigations_User_Prompt.txt", "v1")
        print(f"second_phase_system_prompt: {second_phase_system_prompt}")
        print(f"second_phase_user_prompt: {second_phase_user_prompt}")
        phase2 = self.run_phase2_dread_annotations_mitigations(second_phase_system_prompt, second_phase_user_prompt)
        models = self.build_models()
        phase2 = await self.eval_suggest_improve(second_phase_system_prompt, second_phase_user_prompt, models)
        with open("secondphase_output.txt", "w", encoding="utf-8") as f:
            f.write(phase2)
        #with open("secondphase_output.txt", "r", encoding="utf-8") as f:
            #phase2 = f.read()
        print(f"✅ Phase 2 output preview: {str(phase2)[:1400]}")

        #Third phase
        finalDeliverySystemPrompt = self.load_prompt("finalDeliverySystemPrompt.txt", "v1")
        finalDeliveryUserPrompt = self.load_prompt("finalDeliveryUserPrompt.txt", "v1")
        # Add phase 1+2 to the final delivery user prompt
        finalDeliveryUserPrompt = finalDeliveryUserPrompt + "\n\n" + phase1 + "\n\n" + phase2
        with open("finalDeliveryUserPrompt.txt", 'w', encoding='utf-8') as f:
            f.write(finalDeliveryUserPrompt)
          
        final_report = await self.run_phase3_final_report(finalDeliverySystemPrompt, finalDeliveryUserPrompt)
        
        # Save final report with datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_report_{timestamp}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(final_report)
        print(f"Final report saved to: {filename}")
        
        return "Done"


if __name__ == "__main__":
    

    agent = SimplifiedSecurityDesignReviewAgent()
    result = asyncio.run(agent.run_multistep_review())
    
    # Read firstphaseunmergedoutputs.json file and reconstruct outputs variable
    #with open('firstphaseunmergedoutputs.json', 'r', encoding='utf-8') as f:
    #    parsed_outputs = json.load(f)
    
    # Reconstruct the original outputs variable (list of JSON strings)
    #outputs = [json.dumps(output, ensure_ascii=False) for output in parsed_outputs]
    
    print(result)
