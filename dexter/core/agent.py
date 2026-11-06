"""The Dexter agent loop.

Uses a model-agnostic JSON protocol (ReAct-style) so it works with *any*
OpenRouter free model, including ones without native function-calling. On each
step the model replies with a single JSON object that is either a tool call or
a final spoken answer. Dexter executes granted tools, feeds results back, and
iterates until the model produces an answer (or a step budget is reached).

Progress is streamed out through an async callback so the UI can show the
JARVIS-style "thinking / acting" trace live.
"""
from __future__ import annotations

import json
import re
from typing import Awaitable, Callable, Dict, List, Optional

from .llm import LLMError, OpenRouterClient
from .memory import Memory
from ..tools.registry import ToolRegistry

Emitter = Callable[[Dict[str, object]], Awaitable[None]]

SYSTEM_TEMPLATE = """You are Dexter Cyber, an advanced JARVIS-style personal assistant that operates \
the user's own computer with their explicit permission. You are capable, precise, and concise, \
and you address the user respectfully (you may call them "sir" or by name in a friendly, JARVIS tone).

You act by reasoning step by step and using tools. You can ONLY use the tools listed below; they are \
exactly the capabilities the user has granted:

{tools}

PROTOCOL — every message you send MUST be a single JSON object and nothing else:
  To use a tool:
    {{"thought": "<short reasoning>", "action": {{"tool": "<tool_name>", "args": {{...}}}}}}
  To finish and speak to the user:
    {{"thought": "<short reasoning>", "speak": "<your reply to the user>"}}

Rules:
- Output ONLY the JSON object. No markdown, no prose outside it.
- Take one action at a time, then wait for the OBSERVATION before the next step.
- To act on screen, first use see_screen to find elements and their coordinates, then move/click/type.
- Surface useful information visually: when you have results, lists, numbers or options to show, call
  show_card so the user sees it on the HUD. When juggling several steps, track them with add_task /
  update_task so the on-screen task board reflects your progress (multi-tasking).
- If the user asks to clear/hide the cards, call clear_cards.
- If a capability you need is not in the tool list, it was not granted — explain that in "speak".
- Never pretend to have done something you did not do. If a tool returns an error, deal with it honestly.
- Keep going until the task is done, then give a short, friendly spoken summary.

Operating system / environment note: {env}
"""


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort extraction of the JSON object from a model reply."""
    text = text.strip()
    # Strip code fences if present.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = _JSON_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


class DexterAgent:
    def __init__(
        self,
        llm: OpenRouterClient,
        tools: ToolRegistry,
        memory: Memory,
        env_note: str = "",
        max_steps: int = 10,
    ):
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.env_note = env_note or "unknown"
        self.max_steps = max_steps

    def _system_prompt(self) -> str:
        return SYSTEM_TEMPLATE.format(
            tools=self.tools.catalogue_for_prompt(),
            env=self.env_note,
        )

    async def handle(self, user_text: str, emit: Emitter) -> str:
        """Run the agent on a user message; stream events; return final speech."""
        self.memory.add("user", user_text)

        # Build the working message list for this run.
        messages: List[Dict[str, str]] = [{"role": "system", "content": self._system_prompt()}]
        messages += self.memory.recent(limit=20)

        final_speech = ""
        for step in range(1, self.max_steps + 1):
            try:
                raw = await self.llm.chat(messages, temperature=0.3, max_tokens=1200)
            except LLMError as exc:
                final_speech = f"I hit a problem reaching my brain: {exc}"
                await emit({"type": "error", "message": str(exc)})
                break

            data = _extract_json(raw)
            if not data:
                # Model didn't follow the protocol — treat the whole reply as speech.
                final_speech = raw.strip()
                await emit({"type": "speak", "text": final_speech})
                break

            thought = str(data.get("thought", "")).strip()
            if thought:
                await emit({"type": "thought", "text": thought, "step": step})

            if "speak" in data and "action" not in data:
                final_speech = str(data.get("speak", "")).strip()
                await emit({"type": "speak", "text": final_speech})
                break

            action = data.get("action") or {}
            tool_name = str(action.get("tool", "")).strip()
            tool_args = action.get("args") or {}
            if not isinstance(tool_args, dict):
                tool_args = {}

            if not tool_name:
                final_speech = str(data.get("speak", "")).strip() or "Done."
                await emit({"type": "speak", "text": final_speech})
                break

            await emit({"type": "action", "tool": tool_name, "args": tool_args, "step": step})

            observation = await self.tools.dispatch(tool_name, tool_args, emit)
            await emit({"type": "observation", "tool": tool_name, "result": observation, "step": step})

            # Record the step so the model keeps context across the loop.
            messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
            messages.append({"role": "user", "content": f"OBSERVATION: {observation}"})
        else:
            final_speech = "I reached my step limit before finishing. Here is where I got to — ask me to continue if needed."
            await emit({"type": "speak", "text": final_speech})

        if final_speech:
            self.memory.add("assistant", final_speech)
        return final_speech
