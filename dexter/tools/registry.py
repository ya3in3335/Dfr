"""Tool registry: the bridge between the agent brain and real capabilities.

Each tool declares the capability (permission) it requires. Dispatch refuses to
run a tool unless the user has granted that capability. The registry also builds
the human-readable tool catalogue that goes into the agent's system prompt.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

# A pseudo-capability for UI-only tools that are always available (they only
# draw on screen and never touch the OS, so they need no user grant).
UI_CAP = "ui"

Emit = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]

from ..core.llm import OpenRouterClient
from ..core.permissions import PermissionError as DexterPermissionError
from ..core.permissions import PermissionManager
from . import computer, system, vision


@dataclass
class ToolSpec:
    name: str
    capability: str  # required permission key
    description: str
    args: Dict[str, str]  # name -> description (for the prompt)


class ToolRegistry:
    def __init__(self, permissions: PermissionManager, llm: OpenRouterClient):
        self.permissions = permissions
        self.llm = llm
        self._specs: Dict[str, ToolSpec] = {}
        self.tasks: List[Dict[str, Any]] = []  # multi-task board
        self._task_seq = 0
        self._register_all()

    def _cap_ok(self, capability: str) -> bool:
        """UI tools are always available; everything else needs a grant."""
        return capability == UI_CAP or self.permissions.is_granted(capability)

    # -- catalogue -----------------------------------------------------------
    def _add(self, spec: ToolSpec) -> None:
        self._specs[spec.name] = spec

    def _register_all(self) -> None:
        self._add(ToolSpec(
            "see_screen", "screen_vision",
            "Capture the screen and get a description of what is currently visible. "
            "Use this whenever you need to know what is on screen.",
            {"question": "optional: a specific question about the screen"},
        ))
        self._add(ToolSpec(
            "move_mouse", "mouse_keyboard",
            "Move the mouse cursor to absolute pixel coordinates.",
            {"x": "x coordinate", "y": "y coordinate"},
        ))
        self._add(ToolSpec(
            "click", "mouse_keyboard",
            "Click the mouse. Optionally at specific coordinates.",
            {"x": "optional x", "y": "optional y", "button": "left|right|middle", "clicks": "number of clicks"},
        ))
        self._add(ToolSpec(
            "type_text", "mouse_keyboard",
            "Type text using the keyboard.",
            {"text": "the text to type"},
        ))
        self._add(ToolSpec(
            "press_key", "mouse_keyboard",
            "Press a single key (e.g. 'enter', 'esc', 'tab').",
            {"key": "key name"},
        ))
        self._add(ToolSpec(
            "hotkey", "mouse_keyboard",
            "Press a key combination (e.g. ctrl+c).",
            {"keys": "list or '+'-joined keys, e.g. 'ctrl+c'"},
        ))
        self._add(ToolSpec(
            "run_command", "run_commands",
            "Run a shell command on this computer and return its output.",
            {"command": "the shell command"},
        ))
        self._add(ToolSpec(
            "open", "run_commands",
            "Open a file, folder, URL or application with the OS default handler.",
            {"target": "path, url or app"},
        ))
        self._add(ToolSpec(
            "read_file", "read_files",
            "Read the contents of a text file.",
            {"path": "file path"},
        ))
        self._add(ToolSpec(
            "list_dir", "read_files",
            "List the contents of a directory.",
            {"path": "directory path (default '.')"},
        ))
        self._add(ToolSpec(
            "write_file", "write_files",
            "Write (or append to) a text file.",
            {"path": "file path", "content": "text content", "append": "true to append"},
        ))
        self._add(ToolSpec(
            "system_info", "read_files",
            "Report basic information about this computer.",
            {},
        ))
        # --- UI tools (always available; they only draw on the HUD) ---
        self._add(ToolSpec(
            "show_card", UI_CAP,
            "Display a data card on the HUD to show the user information, results or options. "
            "Use this to surface anything worth seeing (lists, summaries, numbers, steps).",
            {"title": "card title", "body": "card text (supports simple line breaks)",
             "accent": "optional color hint: cyan|green|amber|red"},
        ))
        self._add(ToolSpec(
            "clear_cards", UI_CAP,
            "Remove all data cards from the HUD. Use when the user asks to clear or hide the cards.",
            {},
        ))
        self._add(ToolSpec(
            "add_task", UI_CAP,
            "Add a task to the on-screen multi-task board (for tracking several things at once).",
            {"title": "task description"},
        ))
        self._add(ToolSpec(
            "update_task", UI_CAP,
            "Update a task's status on the board.",
            {"id": "task id", "status": "pending|active|done|failed"},
        ))

    def catalogue_for_prompt(self) -> str:
        """Render only the tools the user has currently granted."""
        lines: List[str] = []
        for spec in self._specs.values():
            if not self._cap_ok(spec.capability):
                continue
            arg_desc = ", ".join(f"{k} ({v})" for k, v in spec.args.items()) or "no arguments"
            lines.append(f"- {spec.name}: {spec.description} Args: {arg_desc}")
        if not lines:
            return "(No tools are currently granted. You can only talk.)"
        return "\n".join(lines)

    def granted_tool_names(self) -> List[str]:
        return [s.name for s in self._specs.values() if self._cap_ok(s.capability)]

    # -- dispatch ------------------------------------------------------------
    async def dispatch(self, name: str, args: Dict[str, Any], emit: Emit = None) -> str:
        spec = self._specs.get(name)
        if not spec:
            return f"[unknown tool: {name}]"
        if not self._cap_ok(spec.capability):
            return f"[blocked] The '{spec.capability}' permission is not granted, so '{name}' cannot run."

        try:
            return await self._execute(name, args, emit)
        except DexterPermissionError as exc:
            return f"[blocked] {exc}"
        except Exception as exc:  # keep the loop alive; report back to the model
            return f"[error running {name}: {exc}]"

    async def _emit(self, emit: Emit, event: Dict[str, Any]) -> None:
        if emit is not None:
            try:
                await emit(event)
            except Exception:
                pass

    async def _execute(self, name: str, args: Dict[str, Any], emit: Emit = None) -> str:
        # --- UI / multi-task tools ---
        if name == "show_card":
            card = {
                "id": f"c{int(time.time()*1000)}",
                "title": str(args.get("title", "")).strip() or "Info",
                "body": str(args.get("body", "")).strip(),
                "accent": str(args.get("accent", "cyan")).strip().lower() or "cyan",
            }
            await self._emit(emit, {"type": "card", **card})
            return f"Card '{card['title']}' shown on screen."

        if name == "clear_cards":
            await self._emit(emit, {"type": "clear_cards"})
            return "All cards cleared."

        if name == "add_task":
            self._task_seq += 1
            task = {"id": f"t{self._task_seq}", "title": str(args.get("title", "")).strip(), "status": "pending"}
            self.tasks.append(task)
            await self._emit(emit, {"type": "task", "action": "add", "task": task})
            return f"Task {task['id']} added: {task['title']}"

        if name == "update_task":
            tid = str(args.get("id", "")).strip()
            status = str(args.get("status", "")).strip().lower()
            for t in self.tasks:
                if t["id"] == tid:
                    t["status"] = status
                    await self._emit(emit, {"type": "task", "action": "update", "task": t})
                    return f"Task {tid} → {status}"
            return f"[no such task: {tid}]"

        if name == "see_screen":
            question = args.get("question") or "Describe what is on the screen in detail, including any clickable UI elements and their approximate positions."
            image = vision.capture_screen()
            vision.save_capture(image)
            desc = await self.llm.chat_with_image(
                prompt=question,
                image_bytes=image,
                system="You are the vision system of a desktop assistant. Describe screens precisely and concisely.",
            )
            return f"[screen] {desc}"

        if name == "move_mouse":
            return computer.move_to(int(args["x"]), int(args["y"]))

        if name == "click":
            x = args.get("x"); y = args.get("y")
            return computer.click(
                int(x) if x is not None else None,
                int(y) if y is not None else None,
                button=str(args.get("button", "left")),
                clicks=int(args.get("clicks", 1)),
            )

        if name == "type_text":
            return computer.type_text(str(args.get("text", "")))

        if name == "press_key":
            return computer.press_key(str(args["key"]))

        if name == "hotkey":
            keys = args.get("keys", "")
            parts = keys if isinstance(keys, list) else str(keys).replace(" ", "").split("+")
            return computer.hotkey(*[p for p in parts if p])

        if name == "run_command":
            return system.run_command(str(args["command"]))

        if name == "open":
            return system.open_path(str(args["target"]))

        if name == "read_file":
            return system.read_file(str(args["path"]))

        if name == "list_dir":
            return system.list_dir(str(args.get("path", ".")))

        if name == "write_file":
            return system.write_file(
                str(args["path"]),
                str(args.get("content", "")),
                append=bool(args.get("append", False)),
            )

        if name == "system_info":
            return system.system_info()

        return f"[tool {name} is declared but not implemented]"


def capability_runtime_status() -> Dict[str, bool]:
    """Report which capabilities are actually usable on this machine right now."""
    return {
        "screen_vision": vision.capture_available(),
        "mouse_keyboard": computer.control_available(),
    }
