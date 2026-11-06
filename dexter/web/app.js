/* Dexter Cyber — front-end controller */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const feed = $("feed");
  const orb = $("orb");
  const orbCaption = $("orb-caption");
  const waveform = $("waveform");
  const statusText = $("status-text");
  const connDot = $("conn-dot");

  let ws = null;
  let state = null;

  // ---------- helpers ----------
  function setOrb(mode, caption) {
    orb.classList.remove("listening", "thinking", "speaking");
    if (mode) orb.classList.add(mode);
    waveform.classList.toggle("active", mode === "speaking" || mode === "listening");
    if (caption !== undefined) orbCaption.textContent = caption;
  }

  function addMsg(role, text) {
    const el = document.createElement("div");
    el.className = "msg " + (role === "user" ? "user" : "dexter");
    if (role === "dexter") {
      const who = document.createElement("span");
      who.className = "who";
      who.textContent = "DEXTER";
      el.appendChild(who);
    }
    el.appendChild(document.createTextNode(text));
    feed.appendChild(el);
    feed.scrollTop = feed.scrollHeight;
  }

  function addTrace(html, isErr) {
    const el = document.createElement("div");
    el.className = "trace" + (isErr ? " err" : "");
    el.innerHTML = html;
    feed.appendChild(el);
    feed.scrollTop = feed.scrollHeight;
  }

  function esc(s) {
    return String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  }

  // ---------- state / rendering ----------
  async function loadState() {
    const r = await fetch("/api/state");
    state = await r.json();
    render();
    return state;
  }

  function render() {
    if (!state) return;
    $("model-text").textContent = state.text_model || "—";
    $("model-vision").textContent = state.vision_model || "—";
    const api = $("api-status");
    api.textContent = state.has_api_key ? "configured ✓" : "missing — set OPENROUTER_API_KEY";
    api.className = "field-value " + (state.has_api_key ? "good" : "bad");

    if (!state.consent.accepted) {
      renderConsentList($("consent-list"), false);
      $("consent").classList.remove("hidden");
    } else {
      $("consent").classList.add("hidden");
    }
    renderConsentList($("settings-caps"), true);

    if (!state.has_api_key) {
      orbCaption.textContent = "⚠ No API key — set OPENROUTER_API_KEY in .env";
    }
  }

  function renderConsentList(container, compact) {
    container.innerHTML = "";
    for (const cap of state.consent.capabilities) {
      const card = document.createElement("div");
      card.className = "cap";
      const checked = compact ? cap.granted : true;
      card.innerHTML = `
        <div class="cap-main">
          <h4>${esc(cap.title)} <span class="risk ${cap.risk}">${cap.risk.toUpperCase()}</span></h4>
          <p>${esc(cap.description)}</p>
        </div>
        <label class="switch">
          <input type="checkbox" data-key="${cap.key}" ${checked ? "checked" : ""}/>
          <span class="track"></span><span class="knob"></span>
        </label>`;
      const input = card.querySelector("input");
      if (compact) {
        input.addEventListener("change", async () => {
          await fetch("/api/permission", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key: cap.key, value: input.checked }),
          });
          await loadState();
        });
      }
      container.appendChild(card);
    }
  }

  // ---------- consent actions ----------
  $("consent-all").addEventListener("click", () => {
    document.querySelectorAll("#consent-list input").forEach((i) => (i.checked = true));
  });

  $("consent-accept").addEventListener("click", async () => {
    const grants = {};
    document.querySelectorAll("#consent-list input").forEach((i) => {
      grants[i.dataset.key] = i.checked;
    });
    await fetch("/api/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grants }),
    });
    await loadState();
    connect();
    addMsg("dexter", "Systems online. All authorized capabilities are at your command. How can I help?");
  });

  // ---------- settings ----------
  $("open-settings").addEventListener("click", () => $("settings").classList.remove("hidden"));
  $("settings-close").addEventListener("click", () => $("settings").classList.add("hidden"));
  $("clear-memory").addEventListener("click", async () => {
    await fetch("/api/clear-memory", { method: "POST" });
    feed.innerHTML = "";
    addMsg("dexter", "Memory cleared.");
  });
  $("reset-consent").addEventListener("click", async () => {
    await fetch("/api/reset-consent", { method: "POST" });
    $("settings").classList.add("hidden");
    await loadState();
  });

  // ---------- websocket ----------
  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => {
      connDot.classList.add("on");
      statusText.textContent = "online";
      setOrb(null, "Standing by.");
    };
    ws.onclose = () => {
      connDot.classList.remove("on");
      statusText.textContent = "offline — reconnecting…";
      setTimeout(connect, 2000);
    };
    ws.onmessage = (ev) => handleEvent(JSON.parse(ev.data));
  }

  function handleEvent(e) {
    switch (e.type) {
      case "status":
        if (e.state === "thinking") setOrb("thinking", "Processing…");
        else setOrb(null, "Standing by.");
        break;
      case "thought":
        addTrace(`<b>thinking</b> · ${esc(e.text)}`);
        break;
      case "action":
        addTrace(`<b>▶ ${esc(e.tool)}</b> ${esc(JSON.stringify(e.args))}`);
        setOrb("thinking", `Running ${e.tool}…`);
        break;
      case "observation": {
        let r = String(e.result || "");
        if (r.length > 260) r = r.slice(0, 260) + "…";
        addTrace(`<b>✓ ${esc(e.tool)}</b> → ${esc(r)}`);
        break;
      }
      case "speak":
        addMsg("dexter", e.text);
        setOrb("speaking", "Speaking.");
        setTimeout(() => setOrb(null, "Standing by."), 1200);
        break;
      case "spoke":
        setOrb("speaking", "Speaking.");
        break;
      case "error":
        addTrace(`<b>error</b> · ${esc(e.message)}`, true);
        setOrb(null, "Standing by.");
        break;
    }
  }

  // ---------- sending ----------
  function send() {
    const input = $("input");
    const text = input.value.trim();
    if (!text) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addTrace("<b>error</b> · not connected", true);
      return;
    }
    addMsg("user", text);
    ws.send(JSON.stringify({ type: "chat", text }));
    input.value = "";
  }
  $("send").addEventListener("click", send);
  $("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") send();
  });

  // ---------- browser voice input (optional, client-side) ----------
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = $("mic");
  if (SR) {
    const rec = new SR();
    rec.lang = "en-US";
    rec.interimResults = false;
    let listening = false;
    mic.addEventListener("click", () => {
      if (listening) {
        rec.stop();
        return;
      }
      rec.start();
    });
    rec.onstart = () => {
      listening = true;
      mic.classList.add("active");
      setOrb("listening", "Listening…");
    };
    rec.onend = () => {
      listening = false;
      mic.classList.remove("active");
      setOrb(null, "Standing by.");
    };
    rec.onresult = (ev) => {
      const text = ev.results[0][0].transcript;
      $("input").value = text;
      send();
    };
  } else {
    mic.title = "Voice input not supported in this browser";
    mic.disabled = true;
    mic.style.opacity = 0.4;
  }

  // ---------- boot ----------
  (async function boot() {
    await loadState();
    if (state.consent.accepted) {
      connect();
      addMsg("dexter", "Welcome back. Dexter Cyber online and standing by.");
    }
  })();
})();
