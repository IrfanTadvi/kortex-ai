"""
LLM Client
Unified interface for LLM providers (OpenAI, Anthropic, Local).
Supports streaming and structured outputs.
"""

import json
from typing import List, Dict, Any, AsyncGenerator, Optional
from loguru import logger

from app.config import get_settings


class LLMClient:
    """
    Unified LLM interface supporting multiple providers.
    
    Architecture Decision: Abstracting the LLM layer allows seamless
    switching between providers and supports fallback strategies.
    Streaming is implemented via async generators for real-time UI updates.
    """

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    def _init_client(self):
        """Initialize the appropriate LLM client."""
        if self._client is not None:
            return

        if self.settings.llm_provider == "openai":
            from openai import AsyncOpenAI
            kwargs = {"api_key": self.settings.openai_api_key}
            if self.settings.openai_base_url:
                kwargs["base_url"] = self.settings.openai_base_url
            self._client = AsyncOpenAI(**kwargs)
        elif self.settings.llm_provider == "anthropic":
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        system_prompt: str = None,
    ) -> str:
        """Generate a complete response."""
        self._init_client()

        if self.settings.llm_provider == "openai":
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages

            response = await self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content

        elif self.settings.llm_provider == "anthropic":
            response = await self._client.messages.create(
                model=self.settings.llm_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages,
            )
            return response.content[0].text

        raise ValueError(f"Unknown LLM provider: {self.settings.llm_provider}")

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        system_prompt: str = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response token-by-token."""
        self._init_client()

        if self.settings.llm_provider == "openai":
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages

            stream = await self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        elif self.settings.llm_provider == "anthropic":
            async with self._client.messages.stream(
                model=self.settings.llm_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        system_prompt: str = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON output."""
        structured_prompt = (
            f"{system_prompt or ''}\n\n"
            f"You must respond with valid JSON matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            f"Respond ONLY with the JSON object, no other text."
        )

        response = await self.generate(
            messages=messages,
            system_prompt=structured_prompt,
            temperature=0.1,
        )

        # Parse JSON response
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse structured LLM response: {e}")
            return {}
