"""A scripted chat model, so the harness runs under test with no vendor key."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable


class ToolBindingFakeChatModel(GenericFakeChatModel):
    """`GenericFakeChatModel` that accepts `bind_tools`, so `create_agent(..., tools=[...])` works.

    The base class raises `NotImplementedError`; here binding is a no-op that returns the model
    itself, so the scripted responses drive the agent loop unchanged. The parameter types are
    wider than the base class's (`object` for what it types as `Any`), which pyright strict
    accepts for an override and keeps `Any` out of this module.
    """

    def bind_tools(
        self,
        tools: Sequence[object],
        *,
        tool_choice: str | None = None,
        **kwargs: object,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        del tools, tool_choice, kwargs
        return self


def fake_llm(responses: Sequence[str | AIMessage]) -> ToolBindingFakeChatModel:
    """Each `invoke` returns the next response in order; an `AIMessage` can carry tool calls.

    `bind_tools` is a no-op, so the result drives `langchain.agents.create_agent` with tools.
    """
    return ToolBindingFakeChatModel(messages=iter(responses))
