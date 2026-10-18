const IdentityManager = {
  hasProfile: false,

  async load() {
    this.checkProfile();
    this.populateCompareOptions();
  },

  async checkProfile() {
    const statusBox = document.getElementById("identity-profile-status");
    const deleteBtn = document.getElementById("btn-delete-identity");
    const submitBtn = document.getElementById("btn-save-identity");

    try {
      const res = await App.apiFetch("/api/identity/profile");
      if (res.ok) {
        const data = await res.json();
        this.hasProfile = data.has_profile;
        if (data.has_profile) {
          statusBox.innerHTML = `
            <span class="badge badge-clean">Active Reference Profile</span>
            <div style="margin-top:6px;">Subject: <strong>${data.full_name || "Self"}</strong></div>
            <div style="font-size:11px; color:var(--text-muted);">Consent recorded on: ${new Date(data.consent_recorded_at).toLocaleDateString()}</div>
          `;
          deleteBtn.style.display = "inline-flex";
          submitBtn.textContent = "Replace Reference Image";
        } else {
          statusBox.innerHTML = `<span class="badge badge-setup">No Reference Profile Registered</span>`;
          deleteBtn.style.display = "none";
          submitBtn.textContent = "Register Profile";
        }
      }
    } catch (e) {
      console.warn(e);
    }
  },

  async populateCompareOptions() {
    const select = document.getElementById("identity-compare-select");
    if (!select) return;

    try {
      const res = await App.apiFetch("/api/analysis/history");
      if (res.ok) {
        const records = await res.json();
        select.innerHTML = records.map(r => `
          <option value="${r.id}">${r.original_filename} (${r.media_type} - ${r.assessment})</option>
        `).join("");
      }
    } catch (e) {}
  },

  init() {
    // Identity form
    const form = document.getElementById("identity-profile-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById("identity-file-input");
        const fullName = document.getElementById("identity-fullname").value.trim();
        const consent = document.getElementById("identity-consent").checked;

        if (!fileInput.files || !fileInput.files[0]) {
          App.showToast("Please select a reference portrait photograph.", "danger");
          return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        formData.append("consent", consent);
        if (fullName) formData.append("full_name", fullName);

        try {
          const res = await App.apiFetch("/api/identity/profile", {
            method: "POST",
            body: formData
          });

          const data = await res.json();
          if (res.ok) {
            App.showToast("Reference profile registered securely.", "success");
            this.checkProfile();
          } else {
            App.showToast(data.detail || "Registration failed.", "danger");
          }
        } catch (err) {
          App.showToast("Failed to upload reference profile.", "danger");
        }
      });
    }

    // Delete profile
    const delBtn = document.getElementById("btn-delete-identity");
    if (delBtn) {
      delBtn.addEventListener("click", async () => {
        if (!confirm("Permanently delete your reference photograph and biometric embedding?")) return;
        try {
          const res = await App.apiFetch("/api/identity/profile", { method: "DELETE" });
          if (res.ok) {
            App.showToast("Identity reference erased.", "success");
            this.checkProfile();
          }
        } catch (e) {
          App.showToast("Failed to delete identity profile.", "danger");
        }
      });
    }

    // Threshold slider
    const threshSlider = document.getElementById("identity-threshold");
    const threshLabel = document.getElementById("thresh-val");
    if (threshSlider && threshLabel) {
      threshSlider.addEventListener("input", (e) => {
        threshLabel.textContent = `${Math.round(e.target.value * 100)}%`;
      });
    }

    // Likeness Compare button
    const runCompareBtn = document.getElementById("btn-run-likeness-compare");
    if (runCompareBtn) {
      runCompareBtn.addEventListener("click", async () => {
        const select = document.getElementById("identity-compare-select");
        const analysisId = select.value;
        const threshold = parseFloat(threshSlider.value);

        if (!analysisId) {
          App.showToast("No analysis available to compare.", "warning");
          return;
        }

        try {
          const res = await App.apiFetch("/api/identity/compare", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ analysis_id: analysisId, threshold: threshold })
          });

          const data = await res.json();
          const resultBox = document.getElementById("likeness-result-box");
          const scoreVal = document.getElementById("likeness-score-val");
          const statusVal = document.getElementById("likeness-status-val");

          resultBox.style.display = "block";
          if (data.comparison_possible) {
            scoreVal.textContent = `${(data.similarity_score * 100).toFixed(1)}%`;
            if (data.likeness_match) {
              statusVal.innerHTML = `<span class="badge badge-suspicious">Potential Likeness Match Exceeds Threshold</span><p style="font-size:11px; color:var(--text-secondary); margin-top:6px;">${data.confidence_notes}</p>`;
            } else {
              statusVal.innerHTML = `<span class="badge badge-clean">No Significant Correlation</span><p style="font-size:11px; color:var(--text-secondary); margin-top:6px;">${data.confidence_notes}</p>`;
            }
          } else {
            scoreVal.textContent = "N/A";
            statusVal.innerHTML = `<span class="badge badge-inconclusive">Comparison Inconclusive</span><p style="font-size:11px; color:var(--text-secondary); margin-top:6px;">${data.confidence_notes}</p>`;
          }
        } catch (e) {
          App.showToast("Likeness comparison error.", "danger");
        }
      });
    }

    // Hash modal
    const hashBtn = document.getElementById("btn-verify-hash-modal");
    const hashModal = document.getElementById("hash-modal");
    const closeHashBtn = document.getElementById("btn-close-hash-modal");
    const execHashBtn = document.getElementById("btn-execute-hash-verify");

    if (hashBtn && hashModal) {
      hashBtn.addEventListener("click", () => hashModal.classList.add("open"));
      closeHashBtn.addEventListener("click", () => hashModal.classList.remove("open"));

      execHashBtn.addEventListener("click", async () => {
        const hashVal = document.getElementById("verify-hash-input").value.trim();
        const resBox = document.getElementById("hash-verify-result");
        if (hashVal.length !== 64) {
          App.showToast("SHA-256 hash must be exactly 64 hexadecimal characters.", "danger");
          return;
        }

        try {
          const res = await App.apiFetch("/api/evidence/verify-hash", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_hash: hashVal })
          });

          const data = await res.json();
          resBox.style.display = "block";
          if (data.match_found) {
            resBox.innerHTML = `
              <div class="badge badge-clean" style="margin-bottom:8px;">Match Found in Evidence Vault</div>
              <div>Matched ${data.total_matches} record(s): <strong>${data.matches[0].filename}</strong></div>
              <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Original Ingestion: ${new Date(data.matches[0].timestamp).toLocaleString()}</div>
            `;
          } else {
            resBox.innerHTML = `
              <div class="badge badge-inconclusive">No Matching Bitstream Hash Recorded</div>
              <p style="font-size:12px; color:var(--text-secondary); margin-top:6px;">
                This specific bitstream hash has not been previously analyzed in your vault.
              </p>
            `;
          }
        } catch (e) {
          App.showToast("Verification error.", "danger");
        }
      });
    }

    // Incident new button
    const newIncBtn = document.getElementById("btn-new-incident");
    if (newIncBtn) {
      newIncBtn.addEventListener("click", async () => {
        const title = prompt("Enter Incident Title (e.g. Unauthorized Deepfake on Social Media):");
        if (!title) return;
        const platform = prompt("Enter Platform Detected (e.g. TikTok, Twitter, YouTube):") || "Online";
        const desc = prompt("Enter Brief Description:") || "Potential synthetic media misuse incident.";

        try {
          const res = await App.apiFetch("/api/identity/incidents", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, platform_detected: platform, description: desc })
          });
          if (res.ok) {
            App.showToast("Incident logged.", "success");
            this.loadIncidents();
          }
        } catch (e) {
          App.showToast("Failed to log incident.", "danger");
        }
      });
    }
  },

  async loadIncidents() {
    const tbody = document.getElementById("incidents-table-body");
    if (!tbody) return;

    try {
      const res = await App.apiFetch("/api/identity/incidents");
      if (res.ok) {
        const list = await res.json();
        if (list.length === 0) {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No incidents recorded.</td></tr>`;
          return;
        }

        tbody.innerHTML = list.map(inc => `
          <tr>
            <td><strong>${inc.title}</strong></td>
            <td><span class="format-pill">${inc.platform_detected || "General"}</span></td>
            <td><span class="badge badge-suspicious">${inc.status}</span></td>
            <td style="font-size:12px; color:var(--text-muted);">${new Date(inc.created_at).toLocaleDateString()}</td>
            <td>
              <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="alert('${inc.recommended_steps.replace(/\n/g, '\\n')}')">Forensic Steps</button>
            </td>
          </tr>
        `).join("");
      }
    } catch (e) {
      console.warn(e);
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  IdentityManager.init();
});
