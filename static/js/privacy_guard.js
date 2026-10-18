// Privacy Guard & Document Redactor Controller
const PrivacyGuard = {
  currentRedactedId: null,
  lastTextScanResult: null,
  lastDocScanResult: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    // Mode Switching Tabs
    document.querySelectorAll(".pg-tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        document.querySelectorAll(".pg-tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        document.querySelectorAll(".pg-tab-pane").forEach(pane => {
          pane.style.display = "none";
        });
        const target = document.getElementById(`pg-tab-${tab}`);
        if (target) {
          target.style.display = "block";
          if (tab === "synthetic" && !this.syntheticRecords) {
            this.loadSyntheticDataset();
          }
        }
      });
    });

    // Sample Text Loader
    const sampleSelect = document.getElementById("pg-sample-select");
    if (sampleSelect) {
      sampleSelect.addEventListener("change", (e) => {
        const val = e.target.value;
        const textarea = document.getElementById("pg-text-input");
        if (val === "synthetic_kyc") {
          textarea.value = `EMPLOYEE KYC & BIOMETRIC VERIFICATION DOSSIER\nFull Name: Vikram Aditya Sharma\nPhone No.: +91 98765 43210\nBlood Group: O+\nGender: Male\nAadhar No.: 2345 6789 0123\nAnnual Income: INR 18,50,000 per annum\nEmail Address: vikram.sharma@enterprise.in\nPAN Card: ABCDE1234F\nRegistered City: Bengaluru, Karnataka\nDesignation: Lead Cybersecurity Architect\nCorporate Division: Threat Intelligence & Forensics`;
        } else if (val === "clean") {
          textarea.value = `WEEKLY ENGINEERING SPRINT PLANNING AGENDA\nDate: Monday, October 19, 2026\nLocation: Conference Room B & Online Stream\n\nDiscussion Topics:\n1. Architecture review for microservices v2.4\n2. Database indexing optimizations for latency reduction\n3. Frontend UI accessibility improvements\n\nAttendees: Frontend Lead, Backend Core Team, Quality Assurance.\nStatus: General Business Document - Zero PII - Verified Safe for AI Prompts.`;
        } else if (val === "low") {
          textarea.value = `CUSTOMER SUPPORT INQUIRY & TICKET DETAILS\nTicket #48192\nFrom: customer.care@partnerplatform.org\nHello Support Team,\nI have a general question about our enterprise software subscription renewal. Please give our office a callback at +91 9876543210 during standard business hours.\nBest regards,\nOperations Desk`;
        } else if (val === "corporate") {
          textarea.value = `INTERNAL CORPORATE MEMORANDUM\nTo: Senior Management\nSubject: Preliminary Market Research & Industry Outlook\nNotice: Non-Disclosure Agreement (NDA) Protected Overview.\n\nSummary:\nOur analysts observed a 12% industry shift toward decentralized threat intelligence networks in Q3. Additional operational guidelines are currently under executive committee review.\nClassification: Proprietary Internal Notice.`;
        } else if (val === "medical") {
          textarea.value = `PATIENT CLINICAL DISCHARGE SUMMARY\nPatient Name: Priya Sharma\nDiagnosis: Patient evaluated for malignant tumor in oncology wing.\nTreatment: Prescribed chemotherapy cycle dosage 50mg weekly.\nBlood Group: O+\nDoctor Contact: +91 9812345678\nClassification: Protected Health Information (PHI).`;
        } else if (val === "phishing") {
          textarea.value = `CRITICAL PHISHING ALERT: COMPROMISED SYSTEM CREDENTIALS\nFrom: security-alert@bank-internal-portal.fake\nUrgent: Your account credentials have been leaked on public pastebins.\nExposed Login: admin@megacorp.internal\nDatabase Password: password=AdminMasterKey2026!\nPrimary Bank Account: 987654321098\nAadhaar Card: 2345 6789 0123\nAPI Access Token: ak_live_9988776655443322\nAction Required: Immediately change your secret credentials.`;
        }
      });
    }

    // Text Scan Form
    const scanBtn = document.getElementById("btn-pg-scan-text");
    if (scanBtn) {
      scanBtn.addEventListener("click", () => this.handleTextScan());
    }

    // Copy Sanitized Text
    const copyBtn = document.getElementById("btn-copy-sanitized");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        const out = document.getElementById("pg-sanitized-output").value;
        if (!out) return;
        navigator.clipboard.writeText(out).then(() => {
          App.showToast("Sanitized text copied to clipboard.", "success");
        });
      });
    }

    // PDF Document Dropzone
    const docDropzone = document.getElementById("pg-doc-dropzone");
    const docFileInput = document.getElementById("pg-doc-file-input");

    if (docDropzone && docFileInput) {
      docDropzone.addEventListener("click", () => docFileInput.click());
      docDropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        docDropzone.classList.add("dragover");
      });
      docDropzone.addEventListener("dragleave", () => {
        docDropzone.classList.remove("dragover");
      });
      docDropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        docDropzone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          this.handleDocumentRedaction(e.dataTransfer.files[0]);
        }
      });
      docFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          this.handleDocumentRedaction(e.target.files[0]);
        }
      });
    }

    // Download Redacted Document Button
    const dlBtn = document.getElementById("btn-download-redacted-doc");
    if (dlBtn) {
      dlBtn.addEventListener("click", () => {
        if (this.currentRedactedId) {
          window.open(`/api/privacy/download-redacted/${this.currentRedactedId}`, "_blank");
        }
      });
    }

    // Export Privacy Forensic Audit Report (Text)
    const exportTextReportBtn = document.getElementById("btn-export-privacy-report");
    if (exportTextReportBtn) {
      exportTextReportBtn.addEventListener("click", () => this.handleExportReport("text"));
    }

    // Export Document Audit Report (PDF/Doc)
    const exportDocReportBtn = document.getElementById("btn-export-doc-audit-report");
    if (exportDocReportBtn) {
      exportDocReportBtn.addEventListener("click", () => this.handleExportReport("doc"));
    }

    // Synthetic Dataset Generate & Download Controls
    const btnGenSyn = document.getElementById("btn-generate-synthetic");
    if (btnGenSyn) {
      btnGenSyn.addEventListener("click", () => this.loadSyntheticDataset(true));
    }

    const btnLoadSynText = document.getElementById("btn-load-synthetic-text");
    if (btnLoadSynText) {
      btnLoadSynText.addEventListener("click", () => this.loadSyntheticIntoScanner());
    }

    document.querySelectorAll(".btn-dl-syn").forEach(btn => {
      btn.addEventListener("click", () => {
        const fmt = btn.getAttribute("data-fmt");
        if (fmt) this.downloadSynthetic(fmt);
      });
    });
  },

  async handleExportReport(type) {
    const results = type === "text" ? this.lastTextScanResult : this.lastDocScanResult;
    const title = type === "text" ? "Scanned_Text_PII_Audit" : (results?.filename || "Scanned_Document_Audit");
    
    if (!results) {
      App.showToast("No active scan data available to export.", "warning");
      return;
    }

    try {
      App.showToast("Compiling official Forensic Privacy Audit PDF report...", "info");
      const token = localStorage.getItem("veritas_token");
      const res = await fetch("/api/privacy/export-report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          title: title,
          scan_results: results
        })
      });

      if (!res.ok) {
        throw new Error("Failed to generate PDF audit report.");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `PhishGuard_Privacy_Audit_${title}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      App.showToast("Audit report downloaded successfully.", "success");
    } catch (e) {
      App.showToast(e.message, "danger");
    }
  },

  async handleTextScan() {
    const text = document.getElementById("pg-text-input").value.trim();
    if (!text) {
      App.showToast("Please enter text or select a sample.", "warning");
      return;
    }

    const btn = document.getElementById("btn-pg-scan-text");
    btn.disabled = true;
    btn.textContent = "Scanning & Redacting PII...";

    try {
      const res = await App.apiFetch("/api/privacy/scan-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Scan failed.");
      }

      const data = await res.json();
      this.lastTextScanResult = data;
      this.renderTextResults(data);
    } catch (e) {
      App.showToast(e.message, "danger");
    } finally {
      btn.disabled = false;
      btn.textContent = "Scan & Redact Sensitive Data";
    }
  },

  renderTextResults(data) {
    const resBox = document.getElementById("pg-text-results-box");
    resBox.style.display = "block";

    // Risk Meter & Tier
    const tierElem = document.getElementById("pg-risk-tier");
    const scoreElem = document.getElementById("pg-risk-score");
    const countElem = document.getElementById("pg-entities-count");

    tierElem.className = "badge";
    if (data.risk_tier === "CRITICAL") {
      tierElem.classList.add("badge-suspicious");
      tierElem.textContent = "CRITICAL PRIVACY RISK";
    } else if (data.risk_tier === "HIGH") {
      tierElem.classList.add("badge-suspicious");
      tierElem.textContent = "HIGH PRIVACY RISK";
    } else if (data.risk_tier === "MEDIUM") {
      tierElem.classList.add("badge-inconclusive");
      tierElem.textContent = "MEDIUM PRIVACY RISK";
    } else if (data.risk_tier === "LOW") {
      tierElem.classList.add("badge-clean");
      tierElem.textContent = "LOW PRIVACY RISK";
    } else {
      tierElem.classList.add("badge-clean");
      tierElem.textContent = "CLEAN / ZERO EXPOSURE";
    }

    scoreElem.textContent = `${data.risk_score} / 100`;
    countElem.textContent = data.total_entities_found;

    // Compliance Warnings
    const compBox = document.getElementById("pg-compliance-box");
    if (data.compliance_violations && data.compliance_violations.length > 0) {
      compBox.style.display = "block";
      compBox.innerHTML = `
        <h5 style="color:var(--status-danger); margin-bottom:8px; font-size:13px;">Statutory Regulatory Exposure:</h5>
        ${data.compliance_violations.map(c => `
          <div style="background:rgba(239,68,68,0.1); border-left:3px solid var(--status-danger); padding:8px 12px; margin-bottom:6px; border-radius:4px;">
            <strong style="color:#fff; font-size:12px;">${c.regulation} (${c.jurisdiction})</strong>
            <p style="font-size:11px; color:var(--text-secondary); margin-top:2px;">${c.violation_risk}</p>
          </div>
        `).join("")}
      `;
    } else {
      compBox.style.display = "none";
    }

    // Findings Table
    const tbody = document.getElementById("pg-findings-table-body");
    if (data.findings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No sensitive PII or confidential tokens detected.</td></tr>`;
    } else {
      tbody.innerHTML = data.findings.map(f => `
        <tr>
          <td><span class="format-pill">${f.category}</span></td>
          <td><code style="color:var(--accent-cyan); font-size:11px;">${f.masked_value}</code></td>
          <td><span class="badge badge-clean">${(f.confidence * 100).toFixed(0)}%</span></td>
          <td style="color:var(--text-muted); font-size:12px;">${f.rule}</td>
        </tr>
      `).join("");
    }

    // Sanitized Output Textarea
    document.getElementById("pg-sanitized-output").value = data.sanitized_text;
  },

  async handleDocumentRedaction(file) {
    const progressBox = document.getElementById("pg-doc-progress");
    const resultBox = document.getElementById("pg-doc-results");
    const statusMsg = document.getElementById("pg-doc-progress-msg");
    const fill = document.getElementById("pg-doc-progress-fill");

    progressBox.style.display = "block";
    resultBox.style.display = "none";
    fill.style.width = "25%";
    statusMsg.textContent = "Scanning document bitstream for 8 sensitive classes...";

    const formData = new FormData();
    formData.append("file", file);

    try {
      fill.style.width = "60%";
      statusMsg.textContent = "Applying permanent vector blackouts on PDF bitstream...";

      const res = await App.apiFetch("/api/privacy/redact-document", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Redaction failed.");
      }

      const data = await res.json();
      this.currentRedactedId = data.redacted_id;
      this.lastDocScanResult = data;

      fill.style.width = "100%";
      statusMsg.textContent = "Redaction complete.";

      setTimeout(() => {
        progressBox.style.display = "none";
        this.renderDocResults(data);
      }, 500);
    } catch (e) {
      progressBox.style.display = "none";
      App.showToast(e.message, "danger");
    }
  },

  renderDocResults(data) {
    const resultBox = document.getElementById("pg-doc-results");
    resultBox.style.display = "block";

    document.getElementById("pg-doc-filename").textContent = data.filename;
    document.getElementById("pg-doc-redactions-count").textContent = data.total_redactions_applied;
    const badge = document.getElementById("pg-doc-risk-badge");
    badge.className = "badge";
    if (data.risk_tier === "CRITICAL") {
      badge.classList.add("badge-suspicious");
      badge.textContent = "CRITICAL PRIVACY RISK";
    } else if (data.risk_tier === "HIGH") {
      badge.classList.add("badge-suspicious");
      badge.textContent = "HIGH PRIVACY RISK";
    } else if (data.risk_tier === "MEDIUM") {
      badge.classList.add("badge-inconclusive");
      badge.textContent = "MEDIUM PRIVACY RISK";
    } else if (data.risk_tier === "LOW") {
      badge.classList.add("badge-clean");
      badge.textContent = "LOW PRIVACY RISK";
    } else {
      badge.classList.add("badge-clean");
      badge.textContent = "CLEAN / ZERO EXPOSURE";
    }
    document.getElementById("pg-doc-msg").textContent = data.message;
  },

  async loadSyntheticDataset(forceRefresh = false) {
    const countSelect = document.getElementById("syn-count-select");
    const count = countSelect ? parseInt(countSelect.value) : 10;
    const tbody = document.getElementById("pg-synthetic-table-body");
    const badge = document.getElementById("syn-records-count-badge");

    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--text-muted); padding:20px;">Synthesizing ${count} realistic PII & KYC records...</td></tr>`;
    }

    try {
      const token = localStorage.getItem("phishguard_token") || localStorage.getItem("veritas_token");
      const res = await fetch(`/api/privacy/synthetic/generate?count=${count}`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });

      if (!res.ok) throw new Error("Failed to generate synthetic dataset.");
      const data = await res.json();
      this.syntheticRecords = data.records || [];

      if (badge) badge.textContent = `${this.syntheticRecords.length} Profiles Synthesized`;

      if (tbody) {
        tbody.innerHTML = "";
        this.syntheticRecords.forEach(r => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><code>${r.record_id}</code></td>
            <td><strong>${r.name}</strong></td>
            <td><code>${r.phone_no}</code></td>
            <td><span class="badge" style="background:rgba(239,68,68,0.15); color:#ef4444; border:1px solid rgba(239,68,68,0.3); font-size:10px;">${r.blood_group}</span></td>
            <td>${r.gender}</td>
            <td><code style="color:var(--accent-cyan);">${r.aadhar_no}</code></td>
            <td><strong>${r.income}</strong></td>
            <td>${r.email}</td>
            <td><code>${r.pan_no}</code></td>
          `;
          tbody.appendChild(tr);
        });
      }
      if (forceRefresh) {
        App.showToast(`Synthesized ${this.syntheticRecords.length} fresh PII records successfully.`, "success");
      }
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--status-danger); padding:20px;">Error generating synthetic dataset: ${err.message}</td></tr>`;
      }
      App.showToast(err.message, "danger");
    }
  },

  async downloadSynthetic(format) {
    const countSelect = document.getElementById("syn-count-select");
    const count = countSelect ? parseInt(countSelect.value) : 10;
    try {
      const token = localStorage.getItem("phishguard_token") || localStorage.getItem("veritas_token");
      const res = await fetch(`/api/privacy/synthetic/download/${format}?count=${count}`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (!res.ok) throw new Error(`Failed to download synthetic dataset (.${format}).`);

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `synthetic_dataset.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      App.showToast(`Synthetic dataset (.${format.toUpperCase()}) downloaded successfully.`, "success");
    } catch (err) {
      App.showToast(err.message, "danger");
    }
  },

  loadSyntheticIntoScanner() {
    if (!this.syntheticRecords || this.syntheticRecords.length === 0) {
      App.showToast("Please generate synthetic records first.", "info");
      return;
    }

    // Convert top records into formatted text
    let dossier = "CONFIDENTIAL APPLICANT KYC & BIOMETRIC REGISTRATION BATCH\n";
    dossier += "=================================================================\n\n";

    this.syntheticRecords.slice(0, 3).forEach((r, idx) => {
      dossier += `RECORD [${r.record_id}] - CANDIDATE PROFILE\n`;
      dossier += `Full Name: ${r.name}\n`;
      dossier += `Phone No.: ${r.phone_no}\n`;
      dossier += `Blood Group: ${r.blood_group}\n`;
      dossier += `Gender: ${r.gender}\n`;
      dossier += `Aadhar No.: ${r.aadhar_no}\n`;
      dossier += `Annual Income: ${r.income}\n`;
      dossier += `PAN Card: ${r.pan_no}\n`;
      dossier += `Email Address: ${r.email}\n`;
      dossier += `City: ${r.city}\n`;
      dossier += `Designation: ${r.designation}\n`;
      dossier += "-----------------------------------------------------------------\n\n";
    });

    // Switch to Text tab
    document.querySelectorAll(".pg-tab-btn").forEach(b => b.classList.remove("active"));
    const textTabBtn = document.querySelector('.pg-tab-btn[data-tab="text"]');
    if (textTabBtn) textTabBtn.classList.add("active");

    document.querySelectorAll(".pg-tab-pane").forEach(pane => pane.style.display = "none");
    const textPane = document.getElementById("pg-tab-text");
    if (textPane) textPane.style.display = "block";

    const textarea = document.getElementById("pg-text-input");
    if (textarea) {
      textarea.value = dossier.trim();
      this.handleTextScan();
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  PrivacyGuard.init();
});
