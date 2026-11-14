"""A scripted chat model, so the harness runs under test with no vendor key."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


def fake_llm(responses: Sequence[str | AIMessage]) -> GenericFakeChatModel:
    """Each `invoke` returns the next response in order; an `AIMessage` can carry tool calls."""
    return GenericFakeChatModel(messages=iter(responses))
