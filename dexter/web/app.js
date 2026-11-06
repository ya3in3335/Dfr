/* Dexter Cyber — front-end controller */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  let ws = null, state = null;
  const orb = $("orb"), caption = $("caption");

  // ====================================================================
  //  Animated waveform (pure canvas — matches the reference orb)
  // ====================================================================
  const canvas = $("wave"), ctx = canvas.getContext("2d");
  let intensity = 0.18, targetIntensity = 0.18, phase = 0;
  const CAPTIONS = {
    idle: "Hi, how can I help you&nbsp;…",
    listening: "Listening&nbsp;…",
    thinking: "Processing&nbsp;…",
    speaking: "",
  };

  function resizeCanvas() {
    const r = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, r.width * dpr);
    canvas.height = Math.max(1, r.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener("resize", resizeCanvas);

  function drawWave() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const mid = h / 2;
    intensity += (targetIntensity - intensity) * 0.08;
    const lines = 9;
    for (let l = 0; l < lines; l++) {
      ctx.beginPath();
      const lp = l / (lines - 1) - 0.5;              // -0.5 .. 0.5
      const amp = (h * 0.42) * intensity * (1 - Math.abs(lp) * 0.5);
      const alpha = 0.10 + 0.14 * (1 - Math.abs(lp) * 1.3);
      ctx.strokeStyle = `rgba(90,220,255,${Math.max(0.05, alpha)})`;
      ctx.lineWidth = 1;
      for (let x = 0; x <= w; x += 2) {
        const t = x / w;                              // 0..1
        const env = Math.exp(-Math.pow((t - 0.5) * 3.2, 2)); // gaussian centre
        const y = mid + Math.sin(t * 15 + phase + lp * 2.4) * amp * env
                      + Math.sin(t * 7 - phase * 0.6) * amp * env * 0.35;
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    // central bright node
    const g = ctx.createRadialGradient(w / 2, mid, 0, w / 2, mid, w * 0.12);
    g.addColorStop(0, `rgba(180,245,255,${0.5 * (0.4 + intensity)})`);
    g.addColorStop(1, "rgba(180,245,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    phase += 0.04 + intensity * 0.12;
    requestAnimationFrame(drawWave);
  }

  function setState(s) {
    orb.dataset.state = s;
    targetIntensity = { idle: 0.18, listening: 0.7, thinking: 0.5, speaking: 0.95 }[s] ?? 0.18;
    if (s !== "speaking" && !state?.__busyText) caption.innerHTML = CAPTIONS[s];
  }

  // ====================================================================
  //  Cards + task board
  // ====================================================================
  function addCard(c) {
    const el = document.createElement("div");
    el.className = "card accent-" + (c.accent || "cyan");
    el.id = c.id;
    el.innerHTML = `<div class="card-head"><h4>${esc(c.title)}</h4>
      <button class="card-x" title="dismiss">✕</button></div>
      <div class="card-body">${esc(c.body)}</div>`;
    el.querySelector(".card-x").addEventListener("click", () => el.remove());
    $("cards").appendChild(el);
  }
  const clearCards = () => ($("cards").innerHTML = "");

  const taskEls = {};
  function upsertTask(t) {
    const board = $("tasks");
    board.classList.remove("hidden");
    let el = taskEls[t.id];
    if (!el) {
      el = document.createElement("div");
      el.innerHTML = `<span class="tdot"></span><span class="ttitle"></span>`;
      $("tasks-list").appendChild(el);
      taskEls[t.id] = el;
    }
    el.className = "task " + (t.status || "pending");
    el.querySelector(".ttitle").textContent = t.title;
  }

  // ====================================================================
  //  Audio playback (Groq neural voice) with reactive waveform
  // ====================================================================
  let audioCtx = null, analyser = null, levelRAF = 0;
  function ensureAudio() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
    }
    if (audioCtx.state === "suspended") audioCtx.resume();
    return audioCtx;
  }
  async function playAudioB64(b64) {
    try {
      ensureAudio();
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const buf = await audioCtx.decodeAudioData(bytes.buffer);
      const src = audioCtx.createBufferSource();
      src.buffer = buf;
      src.connect(analyser);
      analyser.connect(audioCtx.destination);
      setState("speaking");
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        let sum = 0; for (const v of data) sum += v;
        targetIntensity = 0.3 + Math.min(0.7, (sum / data.length) / 140);
        levelRAF = requestAnimationFrame(tick);
      };
      tick();
      src.onended = () => { cancelAnimationFrame(levelRAF); setState("idle"); };
      src.start();
    } catch (e) {
      setState("idle");
    }
  }

  // ====================================================================
  //  State / rendering
  // ====================================================================
  async function loadState() {
    state = await (await fetch("/api/state")).json();
    render();
    return state;
  }
  function render() {
    if (!state) return;
    $("model-text").textContent = state.text_model || "—";
    $("model-vision").textContent = state.vision_model || "—";
    const api = $("api-status");
    api.textContent = state.has_api_key ? "configured ✓" : "missing";
    api.style.color = state.has_api_key ? "var(--cyan)" : "var(--danger)";

    if (!state.consent.accepted) { renderCaps($("consent-list"), false); $("consent").classList.remove("hidden"); }
    else $("consent").classList.add("hidden");
    renderCaps($("settings-caps"), true);
    renderVoiceEngines();

    if (!state.has_api_key && state.consent.accepted) caption.innerHTML = "Set OPENROUTER_API_KEY in .env";
    (state.tasks || []).forEach(upsertTask);
  }
  function renderCaps(container, compact) {
    container.innerHTML = "";
    for (const cap of state.consent.capabilities) {
      const card = document.createElement("div");
      card.className = "cap";
      const checked = compact ? cap.granted : true;
      card.innerHTML = `<div class="cap-main"><h4>${esc(cap.title)}
        <span class="risk ${cap.risk}">${cap.risk.toUpperCase()}</span></h4>
        <p>${esc(cap.description)}</p></div>
        <label class="switch"><input type="checkbox" data-key="${cap.key}" ${checked ? "checked" : ""}/>
        <span class="track"></span><span class="knob"></span></label>`;
      const input = card.querySelector("input");
      if (compact) input.addEventListener("change", async () => {
        await fetch("/api/permission", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: cap.key, value: input.checked }) });
        await loadState();
      });
      container.appendChild(card);
    }
  }
  function renderVoiceEngines() {
    const box = $("voice-engines"); box.innerHTML = "";
    for (const e of state.voice_engines) {
      const el = document.createElement("div");
      el.className = "veng" + (state.voice_engine === e.key ? " sel" : "") + (e.available ? "" : " disabled");
      el.innerHTML = `<span>${esc(e.label)}</span>
        <span class="tagx">${state.voice_engine === e.key ? "selected" : (e.available ? "" : "needs key")}</span>`;
      if (e.available) el.addEventListener("click", async () => {
        await fetch("/api/voice-engine", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ engine: e.key }) });
        await loadState();
      });
      box.appendChild(el);
    }
  }

  // ====================================================================
  //  Consent / settings actions
  // ====================================================================
  $("consent-all").addEventListener("click", () =>
    document.querySelectorAll("#consent-list input").forEach((i) => (i.checked = true)));
  $("consent-accept").addEventListener("click", async () => {
    const grants = {};
    document.querySelectorAll("#consent-list input").forEach((i) => (grants[i.dataset.key] = i.checked));
    await fetch("/api/consent", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grants }) });
    await loadState(); connect();
    caption.innerHTML = "Systems online.";
    setTimeout(() => setState("idle"), 1500);
  });
  $("open-settings").addEventListener("click", () => $("settings").classList.remove("hidden"));
  $("settings-close").addEventListener("click", () => $("settings").classList.add("hidden"));
  $("clear-memory").addEventListener("click", async () => { await fetch("/api/clear-memory", { method: "POST" }); });
  $("reset-consent").addEventListener("click", async () => {
    await fetch("/api/reset-consent", { method: "POST" }); $("settings").classList.add("hidden"); await loadState();
  });

  // ====================================================================
  //  WebSocket
  // ====================================================================
  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => { $("conn-dot").classList.add("on"); setState("idle"); };
    ws.onclose = () => { $("conn-dot").classList.remove("on"); setTimeout(connect, 2000); };
    ws.onmessage = (ev) => handleEvent(JSON.parse(ev.data));
  }
  function busy(text) { state && (state.__busyText = text); if (text) caption.innerHTML = esc(text); }

  function handleEvent(e) {
    switch (e.type) {
      case "sync": (e.tasks || []).forEach(upsertTask); break;
      case "status":
        updateRunBadge(e.running || 0);
        if (e.state === "thinking") { setState("thinking"); }
        else if ((e.running || 0) === 0) { busy(null); setState("idle"); }
        break;
      case "thought": busy(e.text); break;
      case "action": busy("▶ " + e.tool); setState("thinking"); break;
      case "observation": break;
      case "speak":
        busy(null); caption.innerHTML = esc(e.text.length > 90 ? e.text.slice(0, 90) + "…" : e.text);
        setState("speaking"); setTimeout(() => { if ((state?.__running|0) === 0) setState("idle"); }, 2600);
        break;
      case "card": addCard(e); break;
      case "clear_cards": clearCards(); break;
      case "task": upsertTask(e.task); break;
      case "audio": playAudioB64(e.data); break;
      case "spoke": setState("speaking"); setTimeout(() => setState("idle"), 1800); break;
      case "error": busy(null); addCard({ id: "err" + Date.now(), title: "Error", body: e.message, accent: "red" }); setState("idle"); break;
    }
  }
  function updateRunBadge(n) {
    if (state) state.__running = n;
    const b = $("run-badge");
    if (n > 0) { b.textContent = n + " running"; b.classList.remove("hidden"); }
    else b.classList.add("hidden");
  }

  // ====================================================================
  //  Sending
  // ====================================================================
  function send(text) {
    text = (text ?? $("input").value).trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "chat", text }));
    $("input").value = "";
    ensureAudio(); // unlock audio on user gesture
  }
  $("send").addEventListener("click", () => send());
  $("input").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });

  // ====================================================================
  //  Voice input — one-shot mic + always-on wake word
  // ====================================================================
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = $("mic"), listenToggle = $("listen-toggle");
  let wakeOn = false, wakeRec = null, oneShot = null;

  if (SR) {
    // one-shot
    oneShot = new SR(); oneShot.interimResults = false; oneShot.lang = "en-US";
    mic.addEventListener("click", () => { ensureAudio(); try { oneShot.start(); } catch {} });
    oneShot.onstart = () => { mic.classList.add("active"); setState("listening"); };
    oneShot.onend = () => { mic.classList.remove("active"); if (!wakeOn) setState("idle"); };
    oneShot.onresult = (ev) => { const t = ev.results[0][0].transcript; send(t); };

    // always-on wake word
    listenToggle.addEventListener("click", () => wakeOn ? stopWake() : startWake());
  } else {
    mic.disabled = true; mic.style.opacity = .4;
    listenToggle.disabled = true; listenToggle.style.opacity = .4;
  }

  function startWake() {
    ensureAudio();
    wakeOn = true;
    listenToggle.classList.add("on");
    listenToggle.textContent = "🎧 Wake: on";
    const wake = (state?.wake_word || "dexter").toLowerCase();
    wakeRec = new SR();
    wakeRec.continuous = true; wakeRec.interimResults = false; wakeRec.lang = "en-US";
    wakeRec.onresult = (ev) => {
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const txt = ev.results[i][0].transcript.trim();
        const low = txt.toLowerCase();
        if (low.includes(wake)) {
          const cmd = txt.slice(low.indexOf(wake) + wake.length).replace(/^[\s,.:;-]+/, "").trim();
          if (cmd) send(cmd);
          else { setState("listening"); }
        }
      }
    };
    wakeRec.onend = () => { if (wakeOn) { try { wakeRec.start(); } catch {} } }; // auto-restart
    wakeRec.onerror = () => {};
    try { wakeRec.start(); } catch {}
  }
  function stopWake() {
    wakeOn = false;
    listenToggle.classList.remove("on");
    listenToggle.textContent = "🎧 Wake: off";
    try { wakeRec && wakeRec.stop(); } catch {}
    setState("idle");
  }

  // ====================================================================
  //  Boot
  // ====================================================================
  (async function boot() {
    resizeCanvas(); drawWave();
    await loadState();
    if (state.consent.accepted) connect();
  })();
})();
