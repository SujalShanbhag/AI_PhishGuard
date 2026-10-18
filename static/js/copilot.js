// AI PhishGuard — Gemini AI Forensic Copilot & Document Inspector
const Copilot = {
  history: [],
  apiKey: localStorage.getItem("phishguard_gemini_key") || "",
  status: null,
  isSending: false,
  attachedFile: null,

  async init() {
    this.bindEvents();
    await this.fetchStatus();
    this.renderWelcome();
  },

  async fetchStatus() {
    try {
      const res = await App.apiFetch("/api/copilot/status");
      if (res.ok) {
        this.status = await res.json();
        this.updateStatusBadges();
      }
    } catch (e) {
      console.warn("Could not fetch Copilot status:", e);
    }
  },

  updateStatusBadges() {
    const isOnline = this.status && this.status.configured;
    const badgeText = isOnline ? "Google Gemini 2.5 Flash Online" : "Local Forensic Intelligence Engine";
    const badgeClass = isOnline ? "badge-clean" : "badge-inconclusive";

    document.querySelectorAll(".copilot-engine-badge").forEach(el => {
      el.className = `badge copilot-engine-badge ${badgeClass}`;
      el.textContent = badgeText;
    });

    const keyBtn = document.getElementById("btn-copilot-settings");
    if (keyBtn) {
      keyBtn.textContent = isOnline ? "Gemini Key Configured" : "Configure Gemini API Key";
    }
  },

  bindEvents() {
    // Send message on Enter or button click
    const sendBtn = document.getElementById("btn-copilot-send");
    const input = document.getElementById("copilot-input");
    if (sendBtn && input) {
      sendBtn.addEventListener("click", () => this.sendMessage());
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }

    // Floating widget toggle
    const floatingBtn = document.getElementById("copilot-floating-btn");
    const floatingDrawer = document.getElementById("copilot-floating-drawer");
    const closeDrawerBtn = document.getElementById("btn-close-floating-copilot");

    if (floatingBtn && floatingDrawer) {
      floatingBtn.addEventListener("click", () => {
        const isOpen = floatingDrawer.style.display === "flex";
        floatingDrawer.style.display = isOpen ? "none" : "flex";
        if (!isOpen) {
          document.getElementById("floating-copilot-input")?.focus();
        }
      });
    }

    if (closeDrawerBtn && floatingDrawer) {
      closeDrawerBtn.addEventListener("click", () => {
        floatingDrawer.style.display = "none";
      });
    }

    // Floating send
    const floatSendBtn = document.getElementById("btn-floating-send");
    const floatInput = document.getElementById("floating-copilot-input");
    if (floatSendBtn && floatInput) {
      floatSendBtn.addEventListener("click", () => this.sendFloatingMessage());
      floatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendFloatingMessage();
        }
      });
    }

    // Suggestion pills click handler
    document.querySelectorAll(".copilot-prompt-pill").forEach(pill => {
      pill.addEventListener("click", (e) => {
        const prompt = pill.getAttribute("data-prompt");
        if (prompt) {
          const mainInput = document.getElementById("copilot-input");
          if (mainInput) {
            mainInput.value = prompt;
            this.sendMessage();
          }
        }
      });
    });

    // File attachment handler
    const fileAttachBtn = document.getElementById("btn-copilot-attach");
    const fileInput = document.getElementById("copilot-file-attach-input");
    if (fileAttachBtn && fileInput) {
      fileAttachBtn.addEventListener("click", () => fileInput.click());
      fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          this.setAttachedFile(e.target.files[0]);
        }
      });
    }

    // Remove attached file
    const removeAttachBtn = document.getElementById("btn-remove-attachment");
    if (removeAttachBtn) {
      removeAttachBtn.addEventListener("click", () => this.clearAttachedFile());
    }

    // Settings Modal
    const settingsBtn = document.getElementById("btn-copilot-settings");
    const settingsModal = document.getElementById("gemini-settings-modal");
    const closeSettingsBtn = document.getElementById("btn-close-gemini-modal");
    const saveKeyBtn = document.getElementById("btn-save-gemini-key");
    const testKeyBtn = document.getElementById("btn-test-gemini-key");

    if (settingsBtn && settingsModal) {
      settingsBtn.addEventListener("click", () => {
        const keyInput = document.getElementById("input-gemini-api-key");
        if (keyInput) keyInput.value = this.apiKey;
        settingsModal.style.display = "flex";
      });
    }

    if (closeSettingsBtn && settingsModal) {
      closeSettingsBtn.addEventListener("click", () => {
        settingsModal.style.display = "none";
      });
    }

    if (testKeyBtn) {
      testKeyBtn.addEventListener("click", async () => {
        const keyVal = document.getElementById("input-gemini-api-key").value.trim();
        const resBox = document.getElementById("gemini-test-result");
        resBox.style.display = "block";
        resBox.innerHTML = '<span style="color:var(--accent-cyan);">Testing connection to Google Gemini 2.5 Flash...</span>';

        try {
          const res = await App.apiFetch(`/api/copilot/test-connection?api_key=${encodeURIComponent(keyVal)}`, { method: "POST" });
          const data = await res.json();
          if (data.success) {
            resBox.innerHTML = `<span style="color:var(--status-success);">✅ ${data.message}</span>`;
          } else {
            resBox.innerHTML = `<span style="color:var(--status-danger);">❌ ${data.message}</span>`;
          }
        } catch (e) {
          resBox.innerHTML = `<span style="color:var(--status-danger);">❌ Error connecting to server: ${e.message}</span>`;
        }
      });
    }

    if (saveKeyBtn) {
      saveKeyBtn.addEventListener("click", async () => {
        const keyVal = document.getElementById("input-gemini-api-key").value.trim();
        const resBox = document.getElementById("gemini-test-result");
        resBox.style.display = "block";

        if (!keyVal) {
          this.apiKey = "";
          localStorage.removeItem("phishguard_gemini_key");
          App.showToast("Gemini API key cleared. Operating in Local Forensic Engine mode.", "info");
          await this.fetchStatus();
          settingsModal.style.display = "none";
          return;
        }

        try {
          const res = await App.apiFetch("/api/copilot/set-key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: keyVal })
          });

          if (res.ok) {
            const data = await res.json();
            this.apiKey = keyVal;
            localStorage.setItem("phishguard_gemini_key", keyVal);
            App.showToast(data.message, "success");
            await this.fetchStatus();
            settingsModal.style.display = "none";
          } else {
            const err = await res.json();
            resBox.innerHTML = `<span style="color:var(--status-danger);">❌ ${err.detail || "Verification failed"}</span>`;
          }
        } catch (e) {
          resBox.innerHTML = `<span style="color:var(--status-danger);">❌ Error: ${e.message}</span>`;
        }
      });
    }

    // Clear chat
    const clearBtn = document.getElementById("btn-copilot-clear");
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (confirm("Clear current conversation history?")) {
          this.history = [];
          this.renderWelcome();
        }
      });
    }

    // Audit Scanned Media Button
    const auditSelectedBtn = document.getElementById("btn-copilot-audit-selected");
    if (auditSelectedBtn) {
      auditSelectedBtn.addEventListener("click", () => {
        const sel = document.getElementById("copilot-analysis-selector");
        const val = sel ? sel.value : null;
        this.inspectCurrentScanWithGemini(val);
      });
    }

    // Direct Upload & Audit Button
    const directAuditBtn = document.getElementById("btn-copilot-direct-audit");
    if (directAuditBtn) {
      directAuditBtn.addEventListener("click", () => {
        const fileInput = document.getElementById("copilot-file-attach-input");
        if (fileInput) fileInput.click();
      });
    }

    // Modal Close for Audit Results
    const closeAuditModal = document.getElementById("btn-close-audit-modal");
    if (closeAuditModal) {
      closeAuditModal.addEventListener("click", () => {
        document.getElementById("gemini-audit-modal").style.display = "none";
      });
    }
  },

  async populateAnalysisSelector() {
    const sel = document.getElementById("copilot-analysis-selector");
    if (!sel) return;
    try {
      const res = await App.apiFetch("/api/analysis?limit=25");
      if (res.ok) {
        const list = await res.json();
        if (!list || list.length === 0) {
          sel.innerHTML = '<option value="">No previous scans found</option>';
          return;
        }
        sel.innerHTML = list.map(item => {
          const filename = item.filename || item.id.substring(0, 8);
          const score = item.overall_score !== null ? `${(item.overall_score * 100).toFixed(0)}%` : "N/A";
          return `<option value="${item.id}">${filename} (${item.assessment} - ${score})</option>`;
        }).join("");
      }
    } catch (e) {
      console.warn("Could not load scans for copilot selector:", e);
    }
  },

  setAttachedFile(file) {
    this.attachedFile = file;
    const badge = document.getElementById("copilot-attachment-preview");
    const nameEl = document.getElementById("copilot-attachment-name");
    if (badge && nameEl) {
      nameEl.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      badge.style.display = "inline-flex";
    }
    App.showToast(`File attached: ${file.name}`, "info");
  },

  clearAttachedFile() {
    this.attachedFile = null;
    const badge = document.getElementById("copilot-attachment-preview");
    const fileInput = document.getElementById("copilot-file-attach-input");
    if (badge) badge.style.display = "none";
    if (fileInput) fileInput.value = "";
  },

  renderWelcome() {
    const container = document.getElementById("copilot-chat-messages");
    if (!container) return;

    container.innerHTML = `
      <div class="chat-message assistant">
        <div class="chat-avatar">AI</div>
        <div class="chat-bubble">
          <h4>👋 Welcome to AI PhishGuard Copilot</h4>
          <p>I am your interactive digital forensics investigator and cybersecurity copilot. Powered by <strong>Google Gemini Multimodal Vision</strong> and local forensic engines.</p>
          <p style="margin-top:8px;">You can ask me questions, attach documents (marks cards, fee receipts, payment invoices, certificates), or test phishing emails and URLs.</p>
          <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
            <button class="btn btn-secondary copilot-prompt-pill" data-prompt="Analyze a marks card or university certificate for tampered grades and font inconsistencies" style="padding:4px 10px; font-size:12px;">📄 Marks Card Forgery</button>
            <button class="btn btn-secondary copilot-prompt-pill" data-prompt="How do I verify if a fee receipt or bank payment confirmation is authentic or photoshopped?" style="padding:4px 10px; font-size:12px;">🧾 Fee Receipt Fraud</button>
            <button class="btn btn-secondary copilot-prompt-pill" data-prompt="Check an email or SMS message for phishing indicators, SPF/DKIM spoofing, and malicious links" style="padding:4px 10px; font-size:12px;">🎣 Phishing Detection</button>
            <button class="btn btn-secondary copilot-prompt-pill" data-prompt="Explain Indian DPDP Act 2023 compliance and mandatory redaction for Aadhaar and PAN" style="padding:4px 10px; font-size:12px;">🛡️ DPDP & PII Redaction</button>
          </div>
        </div>
      </div>
    `;

    // Re-bind dynamically rendered pills
    container.querySelectorAll(".copilot-prompt-pill").forEach(p => {
      p.addEventListener("click", () => {
        const text = p.getAttribute("data-prompt");
        const input = document.getElementById("copilot-input");
        if (input) {
          input.value = text;
          this.sendMessage();
        }
      });
    });
  },

  async sendMessage() {
    const input = document.getElementById("copilot-input");
    const message = input.value.trim();
    if ((!message && !this.attachedFile) || this.isSending) return;

    this.isSending = true;
    input.value = "";

    const userText = message || (this.attachedFile ? `Forensic inspection requested for: ${this.attachedFile.name}` : "");
    this.appendMessage("user", userText);

    // If file is attached, run multimodal inspection
    if (this.attachedFile) {
      await this.sendMultimodalInspection(this.attachedFile, message);
      this.clearAttachedFile();
      this.isSending = false;
      return;
    }

    // Show typing indicator
    const typingId = this.showTypingIndicator();

    try {
      const res = await App.apiFetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          history: this.history,
          api_key: this.apiKey || undefined
        })
      });

      this.removeTypingIndicator(typingId);

      if (res.ok) {
        const data = await res.json();
        this.history.push({ role: "user", content: userText });
        this.history.push({ role: "model", content: data.reply });
        this.appendMessage("assistant", data.reply, data.engine, data.note || data.warning);
      } else {
        const err = await res.json();
        this.appendMessage("assistant", `❌ Error: ${err.detail || "Failed to generate copilot response."}`);
      }
    } catch (e) {
      this.removeTypingIndicator(typingId);
      this.appendMessage("assistant", `❌ Connection error: ${e.message}`);
    } finally {
      this.isSending = false;
    }
  },

  async sendFloatingMessage() {
    const input = document.getElementById("floating-copilot-input");
    const message = input.value.trim();
    if (!message || this.isSending) return;

    this.isSending = true;
    input.value = "";

    this.appendFloatingMessage("user", message);

    try {
      const res = await App.apiFetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          history: this.history,
          api_key: this.apiKey || undefined
        })
      });

      if (res.ok) {
        const data = await res.json();
        this.history.push({ role: "user", content: message });
        this.history.push({ role: "model", content: data.reply });
        this.appendFloatingMessage("assistant", data.reply, data.engine);
        // Also sync main chat if open
        this.appendMessage("user", message);
        this.appendMessage("assistant", data.reply, data.engine);
      } else {
        this.appendFloatingMessage("assistant", "❌ Could not process response.");
      }
    } catch (e) {
      this.appendFloatingMessage("assistant", `❌ Error: ${e.message}`);
    } finally {
      this.isSending = false;
    }
  },

  async sendMultimodalInspection(file, customPrompt) {
    const typingId = this.showTypingIndicator("Executing Multimodal Forensics with Gemini Vision & ELA...");
    const formData = new FormData();
    formData.append("file", file);
    if (customPrompt) formData.append("prompt", customPrompt);
    if (this.apiKey) formData.append("api_key", this.apiKey);

    try {
      const res = await App.apiFetch("/api/copilot/inspect-file", {
        method: "POST",
        body: formData
      });

      this.removeTypingIndicator(typingId);

      if (res.ok) {
        const data = await res.json();
        this.appendInspectionCard(data);
      } else {
        const err = await res.json();
        this.appendMessage("assistant", `❌ Inspection Failed: ${err.detail || "Could not analyze file"}`);
      }
    } catch (e) {
      this.removeTypingIndicator(typingId);
      this.appendMessage("assistant", `❌ Network error during inspection: ${e.message}`);
    }
  },

  async inspectCurrentScanWithGemini(analysisId) {
    if (!analysisId) {
      if (window.Scanner && Scanner.currentAnalysisId) {
        analysisId = Scanner.currentAnalysisId;
      } else {
        try {
          const res = await App.apiFetch("/api/analysis?limit=1");
          if (res.ok) {
            const list = await res.json();
            if (list && list.length > 0) {
              analysisId = list[0].id;
            }
          }
        } catch (e) {}
      }
    }

    if (!analysisId) {
      App.showToast("No active scan found. Please select an image or document to audit.", "info");
      document.getElementById("copilot-file-attach-input")?.click();
      return;
    }

    App.showToast("Initiating Gemini Deep Forensic Audit...", "info");
    const modal = document.getElementById("gemini-audit-modal");
    const content = document.getElementById("gemini-audit-content");
    if (modal && content) {
      content.innerHTML = `
        <div style="text-align:center; padding:40px;">
          <div class="scanner-spinner" style="width:40px; height:40px; margin:0 auto 16px;"></div>
          <h4>Analyzing Media with Gemini AI & Error Level Analysis...</h4>
          <p style="color:var(--text-secondary); font-size:13px; margin-top:6px;">Inspecting text kerning, font baselines, compression anomalies, and PII markers.</p>
        </div>
      `;
      modal.style.display = "flex";
    }

    try {
      const res = await App.apiFetch(`/api/copilot/inspect-analysis/${analysisId}${this.apiKey ? `?api_key=${encodeURIComponent(this.apiKey)}` : ''}`, {
        method: "POST"
      });

      if (res.ok) {
        const data = await res.json();
        this.renderAuditModal(data);
      } else {
        const err = await res.json();
        if (content) {
          content.innerHTML = `<div style="padding:20px; color:var(--status-danger);">❌ Audit failed: ${err.detail || "Unknown error"}</div>`;
        }
      }
    } catch (e) {
      if (content) {
        content.innerHTML = `<div style="padding:20px; color:var(--status-danger);">❌ Connection error: ${e.message}</div>`;
      }
    }
  },

  renderAuditModal(data) {
    const content = document.getElementById("gemini-audit-content");
    if (!content) return;

    const formattedMd = this.renderMarkdown(data.analysis || "No analysis text returned.");
    const elaImgHtml = data.ela_heatmap_url ? `
      <div style="margin-bottom:20px; background:var(--bg-secondary); padding:16px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
        <div style="font-weight:600; font-size:13px; margin-bottom:8px; color:var(--accent-cyan);">🔬 Error Level Analysis (ELA) Tampering Heatmap</div>
        <img src="${data.ela_heatmap_url}" style="max-width:100%; max-height:280px; object-fit:contain; border-radius:4px; border:1px solid var(--border-color);" alt="ELA Heatmap">
        <p style="font-size:11px; color:var(--text-muted); margin-top:6px;">High-intensity regions highlight pixel variance where grades, text, or dates were edited.</p>
      </div>
    ` : '';

    content.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; border-bottom:1px solid var(--border-color); padding-bottom:12px;">
        <div>
          <h3 style="font-size:18px; font-weight:700;">✨ Gemini AI Deep Forensic Audit</h3>
          <span style="font-size:12px; color:var(--text-secondary); font-family:var(--font-mono);">${data.filename} (${data.file_hash ? data.file_hash.substring(0, 16) + '...' : ''})</span>
        </div>
        <span class="badge ${data.source === 'gemini' ? 'badge-clean' : 'badge-inconclusive'}">${data.engine}</span>
      </div>

      ${elaImgHtml}

      <div class="audit-markdown-body" style="font-size:13px; line-height:1.6; color:var(--text-primary);">
        ${formattedMd}
      </div>

      <div style="margin-top:24px; display:flex; gap:12px; justify-content:flex-end;">
        <button class="btn btn-secondary" onclick="document.getElementById('gemini-audit-modal').style.display='none'">Close Audit</button>
        <button class="btn btn-primary" id="btn-audit-to-copilot">Continue Discussion in Copilot</button>
      </div>
    `;

    document.getElementById("btn-audit-to-copilot")?.addEventListener("click", () => {
      document.getElementById("gemini-audit-modal").style.display = "none";
      App.switchView("copilot");
      this.appendMessage("assistant", data.analysis, data.engine);
    });
  },

  appendMessage(role, text, engineName, note) {
    const container = document.getElementById("copilot-chat-messages");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${role}`;

    const isUser = role === "user";
    const avatar = isUser ? "YOU" : "AI";
    const engineTag = engineName ? `<span class="chat-engine-tag">${engineName}</span>` : "";
    const noteTag = note ? `<div class="chat-note-box">${note}</div>` : "";

    msgDiv.innerHTML = `
      <div class="chat-avatar">${avatar}</div>
      <div class="chat-bubble">
        ${engineTag}
        <div class="chat-text">${isUser ? this.escapeHtml(text) : this.renderMarkdown(text)}</div>
        ${noteTag}
      </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  },

  appendInspectionCard(data) {
    const container = document.getElementById("copilot-chat-messages");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-message assistant";

    const elaImg = data.ela_heatmap_url ? `
      <div style="margin:12px 0;">
        <span style="font-size:12px; font-weight:600; color:var(--accent-cyan);">Error Level Analysis (ELA) Visualization:</span>
        <div style="margin-top:6px;"><img src="${data.ela_heatmap_url}" style="max-height:220px; border-radius:4px; border:1px solid var(--border-color);" alt="ELA"></div>
      </div>
    ` : "";

    msgDiv.innerHTML = `
      <div class="chat-avatar">AI</div>
      <div class="chat-bubble">
        <span class="chat-engine-tag">${data.engine || "Gemini Multimodal Vision"}</span>
        <h4 style="margin:6px 0 10px; color:var(--accent-cyan);">Forensic Inspection: ${this.escapeHtml(data.filename)}</h4>
        ${elaImg}
        <div class="chat-text">${this.renderMarkdown(data.analysis || "")}</div>
      </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  },

  appendFloatingMessage(role, text, engineName) {
    const container = document.getElementById("floating-copilot-messages");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `floating-msg ${role}`;
    msgDiv.innerHTML = `
      <div class="floating-bubble">
        <div style="font-size:12px;">${role === 'user' ? this.escapeHtml(text) : this.renderMarkdown(text)}</div>
        ${engineName ? `<span style="font-size:10px; color:var(--text-muted);">${engineName}</span>` : ''}
      </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  },

  showTypingIndicator(label = "AI Copilot is analyzing...") {
    const container = document.getElementById("copilot-chat-messages");
    if (!container) return null;

    const id = `typing-${Date.now()}`;
    const div = document.createElement("div");
    div.id = id;
    div.className = "chat-message assistant typing";
    div.innerHTML = `
      <div class="chat-avatar">AI</div>
      <div class="chat-bubble typing-bubble">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span style="font-size:12px; color:var(--text-secondary); margin-left:8px;">${label}</span>
      </div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
  },

  removeTypingIndicator(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  },

  renderMarkdown(text) {
    if (!text) return "";
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks
    html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre class="chat-code-block"><code>${code}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>');

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h4 style="margin:12px 0 6px; font-weight:700; color:var(--accent-cyan);">$1</h4>');
    html = html.replace(/^## (.*$)/gim, '<h3 style="margin:14px 0 8px; font-weight:700; color:var(--text-primary);">$1</h3>');
    html = html.replace(/^# (.*$)/gim, '<h2 style="margin:16px 0 10px; font-weight:800; color:var(--text-primary);">$1</h2>');

    // Bold & italic
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Blockquotes
    html = html.replace(/^\> (.*$)/gim, '<blockquote style="border-left:3px solid var(--accent-cyan); padding-left:10px; margin:8px 0; color:var(--text-secondary);">$1</blockquote>');

    // Bullet points
    html = html.replace(/^\* (.*$)/gim, '<li style="margin-left:20px; list-style-type:disc;">$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li style="margin-left:20px; list-style-type:disc;">$1</li>');

    // Paragraph breaks
    html = html.replace(/\n\n/g, '<div style="height:8px;"></div>');
    html = html.replace(/\n/g, '<br>');

    return html;
  },

  escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Copilot.init();
});
