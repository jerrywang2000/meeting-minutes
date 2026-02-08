import asyncio
import logging
import os
from typing import List, Tuple, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.openai import OpenAIProvider
from ollama import AsyncClient

from db import DatabaseManager

# Reuse Pydantic models from transcript_processor
from transcript_processor import SummaryResponse, Block, Section, MeetingNotes, People

load_dotenv()
logger = logging.getLogger(__name__)


class IncrementalSummarizer:
    """
    Handles incremental summarization of a meeting in real-time.
    Manages a rolling summary that gets updated with each new transcript chunk.
    """

    def __init__(self, meeting_id: str, model_provider: str, model_name: str, custom_prompt: str = "", db_manager: DatabaseManager = None):
        self.meeting_id = meeting_id
        self.model_provider = model_provider
        self.model_name = model_name
        self.custom_prompt = custom_prompt
        self.db = db_manager if db_manager else DatabaseManager()
        
        self.rolling_summary = SummaryResponse(
            people=People(title="People", blocks=[]),
            session_summary=Section(title="Session Summary", blocks=[]),
            critical_deadlines=Section(title="Critical Deadlines", blocks=[]),
            key_items_decisions=Section(title="Key Items & Decisions", blocks=[]),
            immediate_action_items=Section(title="Immediate Action Items", blocks=[]),
            next_steps=Section(title="Next Steps", blocks=[]),
            meeting_notes=MeetingNotes(sections=[])
        )
        self.transcript_buffer = ""
        self.llm_agent = None
        self.is_initialized = False
        self.active_clients = []

    async def initialize(self, api_key: Optional[str] = None):
        if self.is_initialized:
            return
        logger.info(f"Initializing LLM for meeting {self.meeting_id} with provider='{self.model_provider}', model='{self.model_name}'")
        llm = None
        
        try:
            if self.model_provider == "claude":
                effective_api_key = api_key or await self.db.get_api_key("claude")
                if not effective_api_key: 
                    logger.error("ANTHROPIC_API_KEY not found")
                    raise ValueError("ANTHROPIC_API_KEY not set")
                llm = AnthropicModel(self.model_name, provider=AnthropicProvider(api_key=effective_api_key))
            elif self.model_provider == "groq":
                effective_api_key = api_key or await self.db.get_api_key("groq")
                if not effective_api_key:
                    logger.error("GROQ_API_KEY not found")
                    raise ValueError("GROQ_API_KEY not set")
                llm = GroqModel(self.model_name, provider=GroqProvider(api_key=effective_api_key))
            elif self.model_provider == "openai":
                effective_api_key = api_key or await self.db.get_api_key("openai")
                if not effective_api_key:
                    logger.error("OPENAI_API_KEY not found")
                    raise ValueError("OPENAI_API_KEY not set")
                llm = OpenAIModel(self.model_name, provider=OpenAIProvider(api_key=effective_api_key))
            elif self.model_provider == "openrouter":
                effective_api_key = api_key or await self.db.get_api_key("openrouter")
                if not effective_api_key:
                    logger.error("OPENROUTER_API_KEY not found")
                    raise ValueError("OPENROUTER_API_KEY not set")
                # OpenRouter is OpenAI-compatible
                llm = OpenAIModel(self.model_name, provider=OpenAIProvider(api_key=effective_api_key, base_url="https://openrouter.ai/api/v1"))
            elif self.model_provider == "custom-openai":
                # For custom-openai, we should ideally have the endpoint too.
                # If not provided, we fallback to OpenAI default.
                effective_api_key = api_key or await self.db.get_api_key("openai")
                llm = OpenAIModel(self.model_name, provider=OpenAIProvider(api_key=effective_api_key))
            elif self.model_provider == "ollama":
                logger.info("Using Ollama AsyncClient for summarization")
                pass
            elif self.model_provider == "builtin-ai":
                logger.warning(f"⚠️ IncrementalSummarizer: 'builtin-ai' provider not yet implemented. Falling back to Ollama.")
                self.model_provider = "ollama"
                # Keep the original model name if it's likely an Ollama model, or use a default
                if not self.model_name or self.model_name == "undefined":
                    self.model_name = "llama3.2:latest"
                logger.info(f"🔄 Fallback configured: provider='ollama', model='{self.model_name}'")
            else:
                logger.error(f"❌ Unsupported model provider: {self.model_provider}")
                raise ValueError(f"Unsupported model provider: {self.model_provider}")
            
            if self.model_provider != "ollama":
                if not llm:
                    raise ValueError(f"LLM object for provider '{self.model_provider}' could not be initialized.")
                self.llm_agent = Agent(llm, result_type=SummaryResponse, result_retries=2)
                logger.info(f"🤖 Pydantic-AI Agent initialized for {self.model_provider}/{self.model_name}")
                
            self.is_initialized = True
            logger.info(f"✨ Summarizer for meeting {self.meeting_id} initialized. Provider: {self.model_provider}, Model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}", exc_info=True)
            raise

    async def add_transcript_chunk(self, new_text_chunk: str, chunk_size_threshold: int = 50) -> SummaryResponse:
        logger.debug(f"Received new chunk: '{new_text_chunk}'")
        if not self.is_initialized:
            raise RuntimeError("Summarizer is not initialized. Call `await .initialize()` first.")

        self.transcript_buffer += " " + new_text_chunk
        char_count = len(self.transcript_buffer)
        logger.debug(f"Buffer char count: {char_count}, Threshold: {chunk_size_threshold}")

        if char_count >= chunk_size_threshold:
            chunk_to_process = self.transcript_buffer
            self.transcript_buffer = ""
            logger.info(f"Processing a chunk of {char_count} characters for meeting {self.meeting_id}.")
            await self._summarize_and_update(chunk_to_process)
        
        return self.rolling_summary

    async def _summarize_and_update(self, chunk_to_process: str):
        prompt = f"""
        Analyze the following meeting transcript chunk. Your task is to extract key information and format it as a single JSON object.

        **Instructions:**
        - Your response MUST be a single, valid JSON object.
        - The JSON object must have these keys: "MeetingName", "People", "SessionSummary", "CriticalDeadlines", "KeyItemsDecisions", "ImmediateActionItems", "NextSteps", "MeetingNotes".
        - "MeetingName" should be a string or null.
        - The other top-level keys should contain an object with a "title" and a "blocks" array.
        - "blocks" must be an array of objects, where each object has "id" (string), "type" (string), "content" (string), and "color" (string).
        - If you cannot find any information for a key, its "blocks" array should be empty.
        - The "content" text should be in Chinese.
        - Respond ONLY with the JSON object.

        **Transcript Chunk:**
        ---
        {chunk_to_process}
        ---
        """
        try:
            logger.debug(f"Calling LLM for meeting {self.meeting_id} with a new chunk.")
            chunk_summary = None
            if self.model_provider == "ollama":
                chunk_summary = await self.chat_ollama_model(self.model_name, prompt)
            else:
                if not self.llm_agent:
                    raise RuntimeError("LLM agent is not initialized for this provider.")
                agent_response = await self.llm_agent.run(prompt)
                if hasattr(agent_response, 'data') and isinstance(agent_response.data, SummaryResponse):
                    chunk_summary = agent_response.data
                elif isinstance(agent_response, SummaryResponse):
                    chunk_summary = agent_response

            if not chunk_summary:
                logger.warning(f"LLM returned no valid summary for chunk in meeting {self.meeting_id}")
                return

            # Merge the chunk_summary into the rolling_summary
            if chunk_summary.meeting_name and not self.rolling_summary.meeting_name:
                self.rolling_summary.meeting_name = chunk_summary.meeting_name
            
            # Use a helper to merge sections
            def merge_section(rolling_section, chunk_section):
                if chunk_section and chunk_section.blocks:
                    rolling_section.blocks.extend(chunk_section.blocks)

            merge_section(self.rolling_summary.people, chunk_summary.people)
            merge_section(self.rolling_summary.session_summary, chunk_summary.session_summary)
            merge_section(self.rolling_summary.critical_deadlines, chunk_summary.critical_deadlines)
            merge_section(self.rolling_summary.key_items_decisions, chunk_summary.key_items_decisions)
            merge_section(self.rolling_summary.immediate_action_items, chunk_summary.immediate_action_items)
            merge_section(self.rolling_summary.next_steps, chunk_summary.next_steps)
            
            # Special handling for nested MeetingNotes
            if chunk_summary.meeting_notes and chunk_summary.meeting_notes.sections:
                if not self.rolling_summary.meeting_notes:
                     self.rolling_summary.meeting_notes = MeetingNotes(sections=[])
                self.rolling_summary.meeting_notes.sections.extend(chunk_summary.meeting_notes.sections)


            logger.info(f"✅ Successfully merged new chunk into rolling summary for {self.meeting_id}")
            # Debug: Print current summary state
            logger.debug(f"📊 Current Summary State for {self.meeting_id}:")
            logger.debug(f"  - People: {len(self.rolling_summary.people.blocks)} blocks")
            logger.debug(f"  - Session Summary: {len(self.rolling_summary.session_summary.blocks)} blocks")
            logger.debug(f"  - Action Items: {len(self.rolling_summary.immediate_action_items.blocks)} blocks")
            if self.rolling_summary.session_summary.blocks:
                logger.debug(f"  - Latest Summary Text: {self.rolling_summary.session_summary.blocks[-1].content[:100]}...")
        except Exception as e:
            logger.error(f"Error updating summary for meeting {self.meeting_id}: {e}", exc_info=True)

    async def chat_ollama_model(self, model_name: str, prompt: str):
        message = {'role': 'system', 'content': prompt}
        ollama_host = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
        client = AsyncClient(host=ollama_host)
        self.active_clients.append(client)
        try:
            # Use format='json' to guide the model
            response = await client.chat(model=model_name, messages=[message], format="json")
            full_response = response['message']['content'].strip()

            if not full_response:
                logger.warning("Ollama returned an empty response.")
                return None
            
            try:
                import json
                # Helper to strip markdown and extract JSON
                def extract_json(text):
                    text = text.strip()
                    if text.startswith('```'):
                        start_index = text.find('{')
                        end_index = text.rfind('}') + 1
                        if start_index != -1 and end_index != -1:
                            return text[start_index:end_index]
                    return text

                clean_json_str = extract_json(full_response)
                logger.debug(f"🔍 [Ollama] Extracted JSON string (first 100 chars): {clean_json_str[:100]}...")
                raw_data = json.loads(clean_json_str)

                # Normalize keys (Ollama sometimes changes casing or returns flat structure)
                # Ensure all required top-level keys exist
                required_keys = ["People", "SessionSummary", "CriticalDeadlines", "KeyItemsDecisions", "ImmediateActionItems", "NextSteps", "MeetingNotes"]
                
                # Case-insensitive key matching
                normalized_data = {}
                logger.debug(f"🔍 [Ollama] Raw JSON keys: {list(raw_data.keys())}")
                for rk in required_keys:
                    # Find if the raw_data has this key (case-insensitive)
                    found_key = next((k for k in raw_data.keys() if k.lower() == rk.lower()), None)
                    if found_key:
                        normalized_data[rk] = raw_data[found_key]
                    else:
                        # Initialize empty if missing
                        if rk == "MeetingNotes":
                            normalized_data[rk] = {"sections": []}
                        else:
                            normalized_data[rk] = {"title": rk, "blocks": []}
                
                # Handle MeetingName separately
                mn_key = next((k for k in raw_data.keys() if k.lower() == "meetingname"), None)
                if mn_key:
                    normalized_data["MeetingName"] = raw_data[mn_key]
                else:
                    normalized_data["MeetingName"] = None
                
                # Fix block types and ensure structure
                def fix_structure(obj, key_name=None):
                    if isinstance(obj, dict):
                        # Fix block types
                        if 'content' in obj:
                            # It's likely a block
                            # 1. Ensure type exists and is valid
                            valid_types = ['bullet', 'heading1', 'heading2', 'text']
                            if 'type' not in obj or obj['type'] not in valid_types:
                                obj['type'] = 'text'
                            
                            # 2. Ensure ID exists
                            if 'id' not in obj or not obj['id']:
                                import uuid
                                obj['id'] = f"block-{uuid.uuid4().hex[:8]}"
                            
                            # 3. Ensure color exists
                            if 'color' not in obj:
                                obj['color'] = ""
                        
                        for k, v in obj.items():
                            fix_structure(v, k)
                    elif isinstance(obj, list):
                        for item in obj:
                            fix_structure(item)

                fix_structure(normalized_data)
                
                # Now validate with Pydantic
                summary = SummaryResponse.model_validate(normalized_data)
                logger.info(f"✅ [Ollama] Validated SummaryResponse. Sections with content: {[k for k, v in normalized_data.items() if isinstance(v, dict) and v.get('blocks')]}")
                return summary
            except Exception as e:
                logger.error(f"Error parsing/validating Ollama response: {e}")
                logger.debug(f"Raw response was: {full_response}")
                raise e
        except asyncio.CancelledError:
            logger.info("Ollama request was cancelled during shutdown")
            raise
        except Exception as e:
            logger.error(f"Error in Ollama chat: {e}")
            raise
        finally:
            if client in self.active_clients:
                self.active_clients.remove(client)

    async def get_final_summary(self) -> SummaryResponse:
        if self.transcript_buffer.strip():
            logger.info(f"Processing final remaining chunk for meeting {self.meeting_id}...")
            await self._summarize_and_update(self.transcript_buffer)
            self.transcript_buffer = ""
        return self.rolling_summary
    
    def cleanup(self):
        logger.info(f"Cleaning up IncrementalSummarizer for meeting {self.meeting_id}")
        try:
            if hasattr(self, 'active_clients') and self.active_clients:
                logger.info(f"Terminating {len(self.active_clients)} active Ollama client sessions")
                for client in self.active_clients:
                    try:
                        if hasattr(client, '_client') and hasattr(client._client, 'close'):
                            asyncio.create_task(client._client.aclose())
                    except Exception as client_error:
                        logger.error(f"Error closing Ollama client: {client_error}", exc_info=True)
                self.active_clients.clear()
                logger.info("All Ollama client sessions terminated")
        except Exception as e:
            logger.error(f"Error during IncrementalSummarizer cleanup: {str(e)}", exc_info=True)