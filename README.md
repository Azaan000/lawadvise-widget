<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>BizAdvise Consulting — AI Assistant</title>
  <style>
    /* ── Demo page styles (optional) ── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #f0f2f5;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #1a1a2e;
    }
    .demo-card {
      background: #fff;
      border-radius: 20px;
      padding: 3rem 3.5rem;
      max-width: 520px;
      width: 90%;
      text-align: center;
      box-shadow: 0 4px 40px rgba(0,0,0,0.08);
    }
    .demo-card h1 { font-size: 1.7rem; font-weight: 700; margin-bottom: 0.75rem; }
    .demo-card p { color: #6b7280; line-height: 1.6; font-size: 0.95rem; }
    .badge {
      display: inline-block;
      background: #e8f5e9;
      color: #2e7d32;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 20px;
      margin-bottom: 1.25rem;
      letter-spacing: 0.03em;
    }

    /* ── Widget styles ── */
    #support-widget-root {
      position: fixed;
      bottom: 28px;
      right: 28px;
      z-index: 9999;
      font-family: 'Segoe UI', system-ui, sans-serif;
    }

    /* Bubble button */
    #sw-bubble {
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: linear-gradient(135deg, #c1121f, #1a1a1a);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 20px rgba(193,18,31,0.45);
      transition: transform 0.2s, box-shadow 0.2s;
      margin-left: auto;
    }
    #sw-bubble:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(193,18,31,0.55); }
    #sw-bubble svg { width: 26px; height: 26px; fill: #fff; transition: opacity 0.2s; }
    #sw-bubble .icon-close { display: none; }

    /* Unread dot */
    #sw-dot {
      width: 11px; height: 11px;
      background: #ff3b30;
      border-radius: 50%;
      border: 2px solid #fff;
      position: absolute;
      top: 2px; right: 2px;
    }

    /* Chat panel */
    #sw-panel {
      position: absolute;
      bottom: 72px;
      right: 0;
      width: 360px;
      background: #fff;
      border-radius: 18px;
      box-shadow: 0 8px 48px rgba(0,0,0,0.16);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transform-origin: bottom right;
      transform: scale(0.85) translateY(12px);
      opacity: 0;
      pointer-events: none;
      transition: transform 0.25s cubic-bezier(.34,1.56,.64,1), opacity 0.2s;
      max-height: 520px;
    }
    #sw-panel.open {
      transform: scale(1) translateY(0);
      opacity: 1;
      pointer-events: all;
    }

    /* Header */
    #sw-header {
      background: linear-gradient(135deg, #c1121f, #1a1a1a);
      padding: 16px 18px 14px;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .sw-avatar {
      width: 40px; height: 40px;
      border-radius: 50%;
      background: rgba(255,255,255,0.2);
      display: flex; align-items: center; justify-content: center;
      font-size: 18px;
      flex-shrink: 0;
    }
    #sw-header h2 { font-size: 0.95rem; font-weight: 600; margin: 0; }
    #sw-header p  { font-size: 0.75rem; opacity: 0.85; margin: 2px 0 0; }
    .sw-online-dot {
      width: 8px; height: 8px;
      background: #4caf50;
      border-radius: 50%;
      display: inline-block;
      margin-right: 4px;
    }

    /* Messages */
    #sw-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #f9fafb;
    }
    #sw-messages::-webkit-scrollbar { width: 4px; }
    #sw-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }

    .sw-msg {
      max-width: 82%;
      padding: 9px 13px;
      border-radius: 14px;
      font-size: 0.875rem;
      line-height: 1.5;
      word-break: break-word;
      animation: sw-pop 0.2s ease;
    }
    @keyframes sw-pop { from { opacity:0; transform: translateY(6px); } to { opacity:1; transform:none; } }
    .sw-msg.bot {
      background: #fff;
      color: #1a1a2e;
      border: 1px solid #e5e7eb;
      border-bottom-left-radius: 4px;
      align-self: flex-start;
    }
    .sw-msg.user {
      background: #c1121f;
      color: #fff;
      border-bottom-right-radius: 4px;
      align-self: flex-end;
    }
    .sw-typing {
      display: flex; gap: 5px; align-items: center;
      padding: 10px 14px;
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 14px;
      border-bottom-left-radius: 4px;
      align-self: flex-start;
      width: fit-content;
    }
    .sw-typing span {
      width: 7px; height: 7px;
      background: #9ca3af;
      border-radius: 50%;
      animation: sw-bounce 1.2s infinite;
    }
    .sw-typing span:nth-child(2) { animation-delay: 0.2s; }
    .sw-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes sw-bounce {
      0%,60%,100% { transform: translateY(0); }
      30% { transform: translateY(-5px); }
    }

    /* Input area */
    #sw-footer {
      padding: 10px 12px;
      border-top: 1px solid #e5e7eb;
      display: flex;
      gap: 8px;
      align-items: flex-end;
      background: #fff;
    }
    #sw-input {
      flex: 1;
      border: 1px solid #e5e7eb;
      border-radius: 22px;
      padding: 9px 14px;
      font-size: 0.875rem;
      resize: none;
      outline: none;
      font-family: inherit;
      max-height: 100px;
      line-height: 1.4;
      transition: border-color 0.15s;
      background: #f9fafb;
      color: #1a1a2e;
    }
    #sw-input:focus { border-color: #c1121f; background: #fff; }
    #sw-send {
      width: 38px; height: 38px;
      border-radius: 50%;
      background: #c1121f;
      border: none;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
      transition: background 0.15s, transform 0.15s;
    }
    #sw-send:hover { background: #8f0d17; transform: scale(1.05); }
    #sw-send:disabled { background: #d1d5db; cursor: not-allowed; transform: none; }
    #sw-send svg { width: 17px; height: 17px; fill: #fff; }

    /* Suggested replies */
    #sw-suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 0 12px 10px;
      background: #fff;
    }
    .sw-suggestion {
      font-size: 0.78rem;
      padding: 5px 11px;
      border-radius: 20px;
      border: 1px solid #c1121f;
      color: #c1121f;
      background: transparent;
      cursor: pointer;
      transition: background 0.15s, color 0.15s;
      font-family: inherit;
    }
    .sw-suggestion:hover { background: #c1121f; color: #fff; }

    .sw-whatsapp-cta {
      display: flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      max-width: 80%;
      margin: 6px 0 12px;
      padding: 9px 14px;
      background: #25D366;
      color: #fff;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: 18px;
      text-decoration: none;
      box-shadow: 0 2px 6px rgba(37,211,102,0.35);
      transition: background 0.15s ease, transform 0.1s ease;
    }
    .sw-whatsapp-cta:hover { background: #1ebe57; transform: translateY(-1px); }
    .sw-whatsapp-cta svg { flex-shrink: 0; }

    @media (max-width: 420px) {
      #sw-panel { width: calc(100vw - 24px); right: -14px; }
    }
  </style>
</head>
<body>

<!-- Demo page content (only for testing; remove on your site) -->
<div class="demo-card">
  <img src="bizadvise-logo.png" alt="BizAdvise Consulting" style="width:90px; margin-bottom:1rem;" />
  <div class="badge">✦ AI Powered</div>
  <h1>BizAdvise Consulting</h1>
  <p>Click the chat bubble in the bottom-right corner to ask about business registration, taxation, accountancy, legal advisory, or digital marketing.</p>
  <br/>
  <p style="font-size:0.82rem; color:#9ca3af;">Powered by Llama 3 via OpenRouter · Built with FastAPI</p>
</div>

<!-- ═══════════════════════════════════════════
     WIDGET — embed this section on your site
═══════════════════════════════════════════ -->

<!-- 1. Place this div where you want the widget to appear -->
<div id="support-widget-root">
  <!-- Notification dot -->
  <div id="sw-dot"></div>

  <!-- Chat panel -->
  <div id="sw-panel" role="dialog" aria-label="Customer support chat">
    <div id="sw-header">
      <div class="sw-avatar"><img src="bizadvise-logo.png" alt="BizAdvise" style="width:100%; height:100%; object-fit:cover; border-radius:50%;" /></div>
      <div>
        <h2>BizAdvise Consulting</h2>
        <p><span class="sw-online-dot"></span>Online · Usually replies instantly</p>
      </div>
    </div>

    <div id="sw-messages" aria-live="polite">
      <!-- Seeded welcome message -->
      <div class="sw-msg bot">👋 Welcome to BizAdvise Consulting! How can we assist you today? Ask me about business registration, taxes, accounting, legal advisory, or digital marketing — or tap a quick option below.</div>
    </div>

    <div id="sw-suggestions">
      <button class="sw-suggestion" onclick="sendSuggestion(this)">🚀 Start a New Business</button>
      <button class="sw-suggestion" onclick="sendSuggestion(this)">💰 File My Taxes</button>
      <button class="sw-suggestion" onclick="sendSuggestion(this)">📊 Manage My Accounts</button>
      <button class="sw-suggestion" onclick="sendSuggestion(this)">⚖️ Legal Assistance</button>
      <button class="sw-suggestion" onclick="sendSuggestion(this)">📈 Grow My Business Online</button>
      <button class="sw-suggestion" onclick="sendSuggestion(this)">👨‍💼 Talk to an Expert</button>
    </div>

    <div id="sw-footer">
      <textarea id="sw-input" rows="1" placeholder="Type your message…" aria-label="Chat message"></textarea>
      <button id="sw-send" aria-label="Send message" disabled>
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
      </button>
    </div>
  </div>

  <!-- Bubble toggle button -->
  <button id="sw-bubble" aria-label="Open support chat">
    <svg class="icon-chat" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
    </svg>
    <svg class="icon-close" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
    </svg>
  </button>
</div>

<!-- 2. Configuration and script -->
<script>
  // ── CONFIGURATION (set these before including the script) ──
  // You can override these by defining window.WIDGET_CONFIG before this script.
  // Example:
  //   <script>
  //     window.WIDGET_CONFIG = {
  //       apiUrl: "https://your-backend.com/chat",
  //       whatsappNumber: "923351340999"
  //     };
  //   </script>
  window.WIDGET_CONFIG = window.WIDGET_CONFIG || {};
  const API_URL = window.WIDGET_CONFIG.apiUrl || "http://localhost:8000/chat";
  const WHATSAPP_NUMBER = window.WIDGET_CONFIG.whatsappNumber || "923351340999";
  const MAX_HISTORY = 20; // messages sent to backend (to avoid token overflow)
  // ────────────────────────────────────────────────────────────

  const bubble   = document.getElementById("sw-bubble");
  const panel    = document.getElementById("sw-panel");
  const messages = document.getElementById("sw-messages");
  const input    = document.getElementById("sw-input");
  const sendBtn  = document.getElementById("sw-send");
  const dot      = document.getElementById("sw-dot");
  const sugBox   = document.getElementById("sw-suggestions");

  let isOpen    = false;
  let isLoading = false;
  let history   = [];

  // Toggle panel
  bubble.addEventListener("click", () => {
    isOpen = !isOpen;
    panel.classList.toggle("open", isOpen);
    bubble.querySelector(".icon-chat").style.display  = isOpen ? "none"  : "block";
    bubble.querySelector(".icon-close").style.display = isOpen ? "block" : "none";
    dot.style.display = "none";
    if (isOpen) {
      setTimeout(() => input.focus(), 100);
    }
  });

  // Auto-resize textarea
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 100) + "px";
    sendBtn.disabled = input.value.trim() === "" || isLoading;
  });

  // Send on Enter (Shift+Enter = newline)
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  sendBtn.addEventListener("click", send);

  // Suggested reply handler
  function sendSuggestion(btn) {
    input.value = btn.textContent;
    sugBox.style.display = "none";
    send();
  }

  // Add message to UI
  function addMessage(role, text, whatsappTopic, timestamp) {
    const div = document.createElement("div");
    div.className = `sw-msg ${role}`;
    if (timestamp) {
      const time = document.createElement("span");
      time.style.fontSize = "0.6rem";
      time.style.opacity = "0.6";
      time.style.display = "block";
      time.textContent = new Date(timestamp).toLocaleTimeString();
      div.appendChild(document.createTextNode(text));
      div.appendChild(time);
    } else {
      div.textContent = text;
    }
    messages.appendChild(div);

    if (whatsappTopic) {
      const encodedText = encodeURIComponent(`Hi, I'm interested in: ${whatsappTopic}`);
      const link = document.createElement("a");
      link.href = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodedText}`;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.className = "sw-whatsapp-cta";
      link.setAttribute("role", "button");
      link.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
          <path d="M12.04 2c-5.52 0-10 4.48-10 10 0 1.77.46 3.45 1.27 4.9L2 22l5.25-1.38a9.94 9.94 0 0 0 4.79 1.22h.01c5.52 0 10-4.48 10-10s-4.49-9.84-10.01-9.84zm0 18.15a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.19 8.19 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24 4.54 0 8.24 3.7 8.24 8.25 0 4.55-3.7 8.23-8.25 8.23zm4.52-6.17c-.25-.12-1.47-.72-1.7-.81-.23-.08-.4-.12-.56.13-.17.25-.64.81-.79.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-2-1.23-.74-.66-1.24-1.47-1.39-1.72-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43.12-.14.16-.25.25-.41.08-.17.04-.31-.02-.43-.06-.12-.56-1.35-.77-1.85-.2-.48-.41-.42-.56-.43-.14-.01-.31-.01-.48-.01-.17 0-.43.06-.66.31s-.87.85-.87 2.08.89 2.41 1.02 2.58c.12.17 1.75 2.67 4.24 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.55.1.47-.07 1.47-.6 1.68-1.18.21-.58.21-1.08.14-1.18-.06-.11-.23-.17-.48-.29z"/>
        </svg>
        Continue on WhatsApp
      `;
      messages.appendChild(link);
    }
    scrollBottom();
    return div;
  }

  function showTyping() {
    const t = document.createElement("div");
    t.className = "sw-typing";
    t.id = "sw-typing-indicator";
    t.setAttribute("aria-label", "Bot is typing");
    t.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(t);
    scrollBottom();
  }

  function hideTyping() {
    const t = document.getElementById("sw-typing-indicator");
    if (t) t.remove();
  }

  function scrollBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  // Send with one automatic retry on failure
  async function sendWithRetry(attempt = 1) {
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history.slice(-MAX_HISTORY) }), // send only last N messages
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = await res.json();
      return data.reply;
    } catch (err) {
      if (attempt < 2) {
        await new Promise(r => setTimeout(r, 1000));
        return sendWithRetry(attempt + 1);
      }
      throw err;
    }
  }

  // Main send function
  async function send() {
    const text = input.value.trim();
    if (!text || isLoading) return;

    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    sugBox.style.display = "none";
    isLoading = true;

    // Add user message
    const userMsg = { role: "user", content: text };
    history.push(userMsg);
    addMessage("user", text, null, Date.now());

    showTyping();

    try {
      const reply = await sendWithRetry();
      hideTyping();

      // Detect WhatsApp tag
      const waMatch = reply.match(/\[WHATSAPP:\s*([^\]]+)\]\s*$/i);
      const displayText = waMatch ? reply.slice(0, waMatch.index).trim() : reply;
      const whatsappTopic = waMatch ? waMatch[1].trim() : null;

      history.push({ role: "assistant", content: displayText });
      addMessage("bot", displayText, whatsappTopic, Date.now());
    } catch (err) {
      hideTyping();
      // Show error with retry button
      const errDiv = document.createElement("div");
      errDiv.className = "sw-msg bot";
      errDiv.innerHTML = `⚠️ Sorry, I couldn't connect. <button onclick="retryLastMessage()" style="background:none;border:1px solid #c1121f;border-radius:12px;padding:2px 10px;cursor:pointer;color:#c1121f;">Retry</button>`;
      messages.appendChild(errDiv);
      scrollBottom();
      console.error("Widget error:", err);
    } finally {
      isLoading = false;
      sendBtn.disabled = input.value.trim() === "";
    }
  }

  // Retry the last user message (removes the error and re-sends)
  async function retryLastMessage() {
    // Remove last bot error message
    const lastMsg = messages.lastElementChild;
    if (lastMsg && lastMsg.classList.contains("sw-msg") && lastMsg.textContent.includes("couldn't connect")) {
      lastMsg.remove();
    }
    // Find last user message in history and re-send
    const lastUserMsg = history.filter(m => m.role === "user").pop();
    if (lastUserMsg) {
      // Remove it from history to avoid duplication
      for (let i = history.length - 1; i >= 0; i--) {
        if (history[i].role === "user" && history[i].content === lastUserMsg.content) {
          history.splice(i, 1);
          break;
        }
      }
      // Remove the user's message from DOM
      const userDivs = messages.querySelectorAll(".sw-msg.user");
      if (userDivs.length) userDivs[userDivs.length - 1].remove();
      // Re-add user message and send
      addMessage("user", lastUserMsg.content, null, Date.now());
      history.push(lastUserMsg);
      send();
    }
  }

  // Expose retry function globally
  window.retryLastMessage = retryLastMessage;
</script>
<!-- ═══════════════════════════════════════════
     End of widget embed code
═══════════════════════════════════════════ -->

</body>
</html>