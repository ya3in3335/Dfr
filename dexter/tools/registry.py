"""Tool registry: the bridge between the agent brain and real capabilities.

Each tool declares the capability (permission) it requires. Dispatch refuses to
run a tool unless the user has granted that capability. The registry also builds
the human-readable tool catalogue that goes into the agent's system prompt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

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
        self._register_all()

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

    def catalogue_for_prompt(self) -> str:
        """Render only the tools the user has currently granted."""
        lines: List[str] = []
        for spec in self._specs.values():
            if not self.permissions.is_granted(spec.capability):
                continue
            arg_desc = ", ".join(f"{k} ({v})" for k, v in spec.args.items()) or "no arguments"
            lines.append(f"- {spec.name}: {spec.description} Args: {arg_desc}")
        if not lines:
            return "(No tools are currently granted. You can only talk.)"
        return "\n".join(lines)

    def granted_tool_names(self) -> List[str]:
        return [s.name for s in self._specs.values() if self.permissions.is_granted(s.capability)]

    # -- dispatch ------------------------------------------------------------
    async def dispatch(self, name: str, args: Dict[str, Any]) -> str:
        spec = self._specs.get(name)
        if not spec:
            return f"[unknown tool: {name}]"
        if not self.permissions.is_granted(spec.capability):
            return f"[blocked] The '{spec.capability}' permission is not granted, so '{name}' cannot run."

        try:
            return await self._execute(name, args)
        except DexterPermissionError as exc:
            return f"[blocked] {exc}"
        except Exception as exc:  # keep the loop alive; report back to the model
            return f"[error running {name}: {exc}]"

    async def _execute(self, name: str, args: Dict[str, Any]) -> str:
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
