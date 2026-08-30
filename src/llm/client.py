from __future__ import annotations

from langchain_openai import ChatOpenAI

import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_llm():
    """
    Return the configured Meridian LLM.

    Uses OpenRouter through LangChain's ChatOpenAI
    integration.
    """

    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
    )

