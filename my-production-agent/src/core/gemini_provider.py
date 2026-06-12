import os
import time
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-3.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # In Gemini, system instruction is passed during model initialization or as a prefix
        # For simplicity in this lab, we'll prepend it if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        # Try generating with primary model, fall back to gemini-3.1-flash-lite if it fails
        fallback_model_name = "gemini-3.1-flash-lite"
        try:
            response = self.model.generate_content(full_prompt)
            active_model_used = self.model_name
        except Exception as e:
            if self.model_name != fallback_model_name:
                print(f"Primary model {self.model_name} failed: {e}. Falling back to {fallback_model_name}...")
                try:
                    fallback_model = genai.GenerativeModel(fallback_model_name)
                    response = fallback_model.generate_content(full_prompt)
                    active_model_used = fallback_model_name
                except Exception as fallback_err:
                    raise fallback_err
            else:
                raise e

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Gemini usage data is in response.usage_metadata
        content = response.text
        usage = {
            "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
            "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(response.usage_metadata, "total_token_count", 0)
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google",
            "model_used": active_model_used
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        fallback_model_name = "gemini-3.1-flash-lite"
        try:
            response = self.model.generate_content(full_prompt, stream=True)
            for chunk in response:
                yield chunk.text
        except Exception as e:
            if self.model_name != fallback_model_name:
                print(f"Primary model {self.model_name} stream failed: {e}. Falling back to {fallback_model_name}...")
                try:
                    fallback_model = genai.GenerativeModel(fallback_model_name)
                    response = fallback_model.generate_content(full_prompt, stream=True)
                    for chunk in response:
                        yield chunk.text
                except Exception as fallback_err:
                    raise fallback_err
            else:
                raise e
