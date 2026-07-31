"""
LLM wrapper supports Anthropic Claude OR OpenAI GPT.

Switch providers by setting LLM_PROVIDER=anthropic or LLM_PROVIDER=openai in .env.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.content.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_anthropic_client = None
_openai_client = None

# Languages a channel may explicitly pin. Anything else falls back to letting
# the model infer the language from the user's own words.
LANGUAGE_NAMES = {
    "rw": "Kinyarwanda",
    "en": "English",
    "fr": "French",
    "sw": "Swahili",
}


def build_system_prompt(language: str | None = None) -> str:
    """
    Return the system prompt, optionally pinned to an explicitly chosen language.

    Channels with a language picker (web chat) pass the user's choice so the
    reply honours it. Channels without one (WhatsApp) pass nothing, and the
    model keeps inferring the language from the message itself.
    """
    name = LANGUAGE_NAMES.get((language or "").strip().lower())
    if not name:
        return SYSTEM_PROMPT

    return SYSTEM_PROMPT + (
        "\n\n# Language override (highest priority)\n"
        f"The user has explicitly selected {name} in the app. Write your entire "
        f"reply in {name} — including hotline guidance and any safety message — "
        "even if their message is written in another language, is very short, or "
        "the earlier conversation used a different language. This rule overrides "
        "the default language rule above."
    )


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
        _anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in .env")
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _ask_anthropic(
    messages: list[dict], max_tokens: int, temperature: float, system: str
) -> str:
    client = _get_anthropic_client()
    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=messages,
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip() or "..."


async def _ask_openai(
    messages: list[dict], max_tokens: int, temperature: float, system: str
) -> str:
    client = _get_openai_client()
    # OpenAI takes system prompt as the first message, not a separate param
    openai_messages = [{"role": "system", "content": system}] + messages
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=openai_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip() or "..."


async def ask_claude(
    messages: list[dict],
    *,
    language: str | None = None,
    max_tokens: int = 600,
    temperature: float = 0.4,
) -> str:
    """
    Send a conversation to the configured LLM and return the text reply.

    `messages` must be a list of {"role": "user"|"assistant", "content": str}.
    `language` pins the reply to a language the user explicitly chose ('rw',
    'en', 'fr', 'sw'); leave it None to let the model follow the user's own
    wording. The function is still named ask_claude for backwards compatibility
    with the routers, but it routes based on settings.llm_provider.
    """
    provider = settings.llm_provider.lower()
    system = build_system_prompt(language)
    try:
        if provider == "openai":
            return await _ask_openai(messages, max_tokens, temperature, system)
        return await _ask_anthropic(messages, max_tokens, temperature, system)
    except Exception as exc:
        logger.exception("LLM API error (provider=%s): %s", provider, exc)
        return (
            "Serivisi yacu ntiri gukora muri iki gihe. Turimo gukemura ikibazo, iragaruka vuba. "
            "Sorry, I'm having trouble right now. Please try again in a moment."
        )
