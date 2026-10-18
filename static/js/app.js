// Core Application Controller
const App = {
  token: localStorage.getItem("veritas_token") || null,
  user: null,
  activeView: "overview",
  currentAnalysis: null,

  async init() {
    this.bindEvents();
    await this.checkAuth();
    await this.fetchCapabilities();
  },

  async apiFetch(endpoint, options = {}) {
    const headers = options.headers || {};
    if (this.token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const config = {
      ...options,
      headers
    };

    try {
      const res = await fetch(endpoint, config);
      if (res.status === 401) {
        this.token = null;
        localStorage.removeItem("veritas_token");
        this.showAuthModal();
        throw new Error("Session expired. Please log in.");
      }
      return res;
    } catch (err) {
      console.error("API Fetch Error:", err);
      throw err;
    }
  },

  async checkAuth() {
    try {
      const res = await this.apiFetch("/api/auth/me");
      if (res.ok) {
        this.user = await res.json();
        document.getElementById("user-display-name").textContent = this.user.full_name || this.user.email;
        document.getElementById("user-display-role").textContent = (this.user.role || "analyst").toUpperCase();
        this.hideAuthModal();
        Dashboard.load();
      } else {
        this.showAuthModal();
      }
    } catch (e) {
      this.showAuthModal();
    }
  },

  async fetchCapabilities() {
    try {
      const res = await fetch("/api/capabilities");
      if (res.ok) {
        const data = await res.json();
        const indicator = document.getElementById("system-cap-status");
        if (data.deepfake_detector_loaded) {
          indicator.textContent = `Online: ${data.model_architecture.toUpperCase()}`;
        } else {
          indicator.textContent = "Setup Required (No Weights)";
          indicator.style.color = "var(--status-warning)";
        }
      }
    } catch (e) {
      console.warn("Could not check capabilities", e);
    }
  },

  switchView(viewName) {
    this.activeView = viewName;
    document.querySelectorAll(".nav-item").forEach(item => {
      item.classList.toggle("active", item.getAttribute("data-view") === viewName);
    });

    document.querySelectorAll(".view-section").forEach(sec => {
      sec.style.display = "none";
    });

    const targetSection = document.getElementById(`view-${viewName}`);
    if (targetSection) {
      targetSection.style.display = "block";
    }

    // Heading update
    const headingMap = {
      overview: "Dashboard Overview",
      scanner: "Document & Media Forensics Scanner",
      evidence: "Evidence & Explainability Explorer",
      datasets: "Datasets Hub & Machine Learning Studio",
      copilot: "AI Forensic Copilot (Powered by Gemini)",
      "privacy-guard": "Privacy Guard (PII Redaction & DPDP Compliance)",
      history: "Digital Evidence Chain & History",
      reports: "Forensic Analysis Reports"
    };
    document.getElementById("page-heading").textContent = headingMap[viewName] || "AI PhishGuard";

    // View-specific initializers
    if (viewName === "overview") Dashboard.load();
    if (viewName === "history") Dashboard.loadHistory();
    if (viewName === "reports") Dashboard.loadReports();
    if (viewName === "evidence" && window.EvidenceExplorer) EvidenceExplorer.init();
    if (viewName === "copilot" && window.Copilot) {
      Copilot.fetchStatus();
      Copilot.populateAnalysisSelector();
    }
    if (viewName === "datasets" && window.DatasetsHub) DatasetsHub.init();
  },

  bindEvents() {
    // Navigation
    document.querySelectorAll(".nav-item").forEach(item => {
      item.addEventListener("click", () => {
        const view = item.getAttribute("data-view");
        this.switchView(view);
      });
    });

    // Auth Mode Switchers
    const tabLogin = document.getElementById("auth-tab-login");
    const tabRegister = document.getElementById("auth-tab-register");
    const panelLogin = document.getElementById("auth-panel-login");
    const panelRegister = document.getElementById("auth-panel-register");

    const switchToLogin = () => {
      if (tabLogin && tabRegister && panelLogin && panelRegister) {
        tabLogin.classList.add("active");
        tabRegister.classList.remove("active");
        panelLogin.style.display = "block";
        panelRegister.style.display = "none";
      }
    };

    const switchToRegister = () => {
      if (tabLogin && tabRegister && panelLogin && panelRegister) {
        tabRegister.classList.add("active");
        tabLogin.classList.remove("active");
        panelRegister.style.display = "block";
        panelLogin.style.display = "none";
      }
    };

    if (tabLogin) tabLogin.addEventListener("click", switchToLogin);
    if (tabRegister) tabRegister.addEventListener("click", switchToRegister);

    const linkToReg = document.getElementById("link-switch-to-register");
    if (linkToReg) linkToReg.addEventListener("click", (e) => { e.preventDefault(); switchToRegister(); });

    const linkToLog = document.getElementById("link-switch-to-login");
    if (linkToLog) linkToLog.addEventListener("click", (e) => { e.preventDefault(); switchToLogin(); });

    // Quick Fill Button
    const btnQuickFill = document.getElementById("btn-quick-fill-login");
    if (btnQuickFill) {
      btnQuickFill.addEventListener("click", () => {
        document.getElementById("auth-email").value = "analyst@phishguard.ai";
        document.getElementById("auth-password").value = "PhishGuardAdmin2026!";
        this.showToast("Test credentials loaded.", "info");
      });
    }

    // Login Form Handler
    const authForm = document.getElementById("auth-form");
    if (authForm) {
      authForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("auth-email").value.trim();
        const password = document.getElementById("auth-password").value;

        try {
          const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
          });

          const data = await res.json();
          if (res.ok) {
            this.token = data.access_token;
            localStorage.setItem("veritas_token", this.token);
            localStorage.setItem("phishguard_token", this.token);
            this.user = data.user;
            this.hideAuthModal();
            this.showToast(`Welcome back, ${data.user.full_name || data.user.email}!`, "success");
            this.checkAuth();
          } else {
            this.showToast(data.detail || "Authentication failed.", "danger");
          }
        } catch (err) {
          this.showToast("Network error authenticating.", "danger");
        }
      });
    }

    // Register Form Handler
    const regForm = document.getElementById("auth-register-form");
    if (regForm) {
      regForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const full_name = document.getElementById("reg-name").value.trim();
        const email = document.getElementById("reg-email").value.trim();
        const role = document.getElementById("reg-role").value;
        const password = document.getElementById("reg-password").value;
        const confirm_pwd = document.getElementById("reg-confirm-password").value;

        if (password !== confirm_pwd) {
          this.showToast("Passwords do not match.", "danger");
          return;
        }

        if (password.length < 8) {
          this.showToast("Password must be at least 8 characters.", "danger");
          return;
        }

        try {
          const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ full_name, email, password, role })
          });

          const data = await res.json();
          if (res.ok) {
            this.token = data.access_token;
            localStorage.setItem("veritas_token", this.token);
            localStorage.setItem("phishguard_token", this.token);
            this.user = data.user;
            this.hideAuthModal();
            this.showToast(`Account registered successfully! Welcome, ${data.user.full_name}.`, "success");
            this.checkAuth();
          } else {
            this.showToast(data.detail || "Registration failed.", "danger");
          }
        } catch (err) {
          this.showToast("Network error registering account.", "danger");
        }
      });
    }

    // Logout
    document.getElementById("btn-logout").addEventListener("click", async () => {
      await fetch("/api/auth/logout", { method: "POST" });
      this.token = null;
      localStorage.removeItem("veritas_token");
      location.reload();
    });

    // Retention save
    document.getElementById("btn-save-retention").addEventListener("click", async () => {
      const days = parseInt(document.getElementById("setting-retention-select").value);
      try {
        const res = await this.apiFetch("/api/auth/retention", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ retention_days: days })
        });
        if (res.ok) {
          this.showToast(`Retention policy updated to ${days} days.`, "success");
        }
      } catch (err) {
        this.showToast("Failed to update retention policy.", "danger");
      }
    });

    // Account wipe
    document.getElementById("btn-wipe-account").addEventListener("click", async () => {
      if (!confirm("Are you sure? This will delete your entire account, all scan records, biometric references, and reports.")) {
        return;
      }
      try {
        const res = await this.apiFetch("/api/auth/me", { method: "DELETE" });
        if (res.ok) {
          alert("Account and data wiped. Logging out.");
          this.token = null;
          localStorage.removeItem("veritas_token");
          location.reload();
        }
      } catch (e) {
        this.showToast("Failed to wipe account.", "danger");
      }
    });
  },

  showAuthModal() {
    document.getElementById("auth-modal").classList.add("open");
  },

  hideAuthModal() {
    document.getElementById("auth-modal").classList.remove("open");
  },

  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
};

document.addEventListener("DOMContentLoaded", () => {
  App.init();
});
