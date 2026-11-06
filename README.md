# Dexter Cyber 🛡️

A **JARVIS-style personal desktop assistant** that runs on *your* computer, powered by **free
OpenRouter models**. Dexter can see your screen, talk back out loud, and operate the machine on
your behalf — all behind a clear, one-time consent screen that you control.

> **You are in charge.** Every sensitive capability (screen capture, mouse/keyboard control,
> running commands, reading/writing files) is granted explicitly on first launch and can be
> toggled off at any time. Consent is stored **only on your machine** and nothing is sent
> anywhere except the OpenRouter AI brain you configure.

---

## ✨ Features

- **Free AI brain** — uses OpenRouter's `:free` models (no cost). Text + vision.
- **Sees the screen** — captures your display and reasons about what's on it via a vision model.
- **Operates the computer** — moves the mouse, clicks, types, runs commands, reads/writes files.
- **Speaks** — offline text-to-speech (`pyttsx3`, the same engine used by the referenced
  [J.A.R.V.I.S project](https://github.com/GauravSingh9356/J.A.R.V.I.S)).
- **Voice input** — browser speech recognition in the UI, plus optional microphone wake-word.
- **JARVIS-style HUD** — arc-reactor interface with a live reasoning/action trace.
- **Permission-first** — one-time authorization, fully granular and revocable.

---

## 🚀 Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your free OpenRouter key
cp .env.example .env
#   then edit .env and set OPENROUTER_API_KEY=...  (get one at https://openrouter.ai/keys)

# 3. Launch
python run.py
```

Your browser opens `http://127.0.0.1:8787`. On first run you'll see the **authorization screen** —
review the capabilities, grant what you want, and Dexter comes online.

---

## 🧠 How it works

```
          ┌──────────────┐     JSON action protocol      ┌───────────────┐
  You ──▶ │  JARVIS HUD  │ ◀── WebSocket (live trace) ──▶ │  Dexter Agent │
          └──────────────┘                                └───────┬───────┘
                                                                  │ picks a granted tool
                         ┌────────────────────────────────────────┼───────────────────────┐
                         ▼                     ▼                    ▼                       ▼
                   see_screen            mouse/keyboard        run_command            read/write files
                 (vision model)          (pyautogui)           (subprocess)              (filesystem)
                         └──────────── every tool checks the Permission layer ───────────┘
```

The agent uses a **model-agnostic JSON protocol**, so it works with any OpenRouter free model —
even ones without native function-calling. On each step the model returns a single JSON object
that is either a tool call or a final spoken answer; Dexter runs granted tools, feeds the result
back, and loops until the task is done.

---

## 🔐 Permissions

| Capability | What it allows | Risk |
|---|---|---|
| See the screen | Screenshot capture for vision | medium |
| Control mouse & keyboard | Move, click, type | high |
| Run system commands | Execute shell commands | high |
| Read files | Read text files | medium |
| Write & edit files | Create/modify files | high |
| Speak out loud | Text-to-speech | low |
| Listen to microphone | Voice commands | medium |
| Access the internet | Reach the AI brain | medium |

Grants are saved to `~/.dexter_cyber/consent.json`. Delete that file (or use **Revoke all &
re-ask** in Settings) to be prompted again.

---

## ⚙️ Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `OPENROUTER_API_KEY` | — | **Required.** Your free OpenRouter key. |
| `DEXTER_TEXT_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | Reasoning model. |
| `DEXTER_VISION_MODEL` | `google/gemini-2.0-flash-exp:free` | Screen-vision model. |
| `DEXTER_HOST` / `DEXTER_PORT` | `127.0.0.1` / `8787` | Local UI address. |
| `DEXTER_VOICE` | `1` | Enable spoken replies. |
| `DEXTER_VOICE_RATE` | `175` | Words per minute. |
| `DEXTER_HOME` | `~/.dexter_cyber` | Where consent/memory/logs live. |

---

## 🖥️ Platform notes

- **Screen capture / control** need a real graphical desktop. On Linux you may also need
  `python3-tk` and `python3-xlib` for `pyautogui`.
- **Voice** needs audio output; the microphone needs `PyAudio` for the server-side listener
  (the browser mic button works without it).
- **Fail-safe:** slam the mouse into the top-left corner to instantly abort any automation.

---

## ⚠️ Responsible use

Dexter controls a real computer. Only grant the capabilities you need, keep it pointed at your own
machine, and review what it does via the live trace. It is a personal productivity assistant — not
a tool for acting against systems you don't own or control.

## 📄 License

MIT — see [LICENSE](LICENSE).
