const Scanner = {
  currentAnalysisId: null,

  init() {
    const dropzone = document.getElementById("scanner-dropzone");
    const fileInput = document.getElementById("scanner-file-input");

    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        this.handleFileUpload(e.target.files[0]);
      }
    });

    document.getElementById("btn-inspect-evidence").addEventListener("click", () => {
      if (this.currentAnalysisId) {
        EvidenceExplorer.loadAnalysis(this.currentAnalysisId);
        App.switchView("evidence");
      }
    });

    document.getElementById("btn-generate-report").addEventListener("click", () => {
      if (this.currentAnalysisId) {
        Dashboard.quickGenerateReport(this.currentAnalysisId);
      }
    });

    const geminiBtn = document.getElementById("btn-scanner-gemini-inspect");
    if (geminiBtn) {
      geminiBtn.addEventListener("click", () => {
        if (window.Copilot) {
          Copilot.inspectCurrentScanWithGemini(this.currentAnalysisId);
        } else {
          App.showToast("Copilot service initializing...", "info");
        }
      });
    }

    const delBtn = document.getElementById("btn-delete-current-analysis");
    if (delBtn) {
      delBtn.addEventListener("click", async () => {
        if (!this.currentAnalysisId) return;
        if (!confirm("Are you sure you want to delete this scan and all associated media files?")) return;
        try {
          const res = await App.apiFetch(`/api/analysis/${this.currentAnalysisId}`, { method: "DELETE" });
          if (res.ok) {
            App.showToast("Analysis and uploaded media deleted successfully.", "success");
            document.getElementById("scanner-result-box").style.display = "none";
            this.currentAnalysisId = null;
            Dashboard.load();
          } else {
            App.showToast("Failed to delete analysis.", "danger");
          }
        } catch (e) {
          App.showToast("Error deleting analysis.", "danger");
        }
      });
    }
  },

  async handleFileUpload(file) {
    const progressBox = document.getElementById("scanner-progress-box");
    const resultBox = document.getElementById("scanner-result-box");
    const fill = document.getElementById("scanner-progress-fill");
    const statusMsg = document.getElementById("scanner-progress-msg");
    const pctMsg = document.getElementById("scanner-progress-pct");

    progressBox.style.display = "block";
    resultBox.style.display = "none";
    fill.style.width = "15%";
    statusMsg.textContent = "Verifying binary file header...";
    pctMsg.textContent = "15%";

    const formData = new FormData();
    formData.append("file", file);

    try {
      fill.style.width = "40%";
      statusMsg.textContent = "Executing neural inference and Error Level Analysis (ELA)...";
      pctMsg.textContent = "40%";

      const res = await App.apiFetch("/api/analysis/image", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload rejected.");
      }

      const initialData = await res.json();
      this.currentAnalysisId = initialData.id;

      fill.style.width = "100%";
      statusMsg.textContent = "Forensics completed.";
      pctMsg.textContent = "100%";
      setTimeout(() => {
        progressBox.style.display = "none";
        this.renderResults(initialData);
      }, 400);
    } catch (e) {
      progressBox.style.display = "none";
      App.showToast(e.message, "danger");
    }
  },

  renderResults(data) {
    const box = document.getElementById("scanner-result-box");
    box.style.display = "block";

    const badge = document.getElementById("result-badge");
    const scoreElem = document.getElementById("result-score");
    const confElem = document.getElementById("result-confidence");
    const hashElem = document.getElementById("result-hash");
    const modelElem = document.getElementById("result-model");
    const facesElem = document.getElementById("result-faces");
    const notesElem = document.getElementById("result-notes");

    badge.className = "badge";
    if (data.assessment === "POTENTIALLY_SUSPICIOUS") {
      badge.classList.add("badge-suspicious");
      badge.textContent = "POTENTIALLY SUSPICIOUS";
    } else if (data.assessment === "NO_STRONG_EVIDENCE") {
      badge.classList.add("badge-clean");
      badge.textContent = "NO STRONG EVIDENCE";
    } else if (data.assessment === "SETUP_REQUIRED") {
      badge.classList.add("badge-setup");
      badge.textContent = "SETUP REQUIRED";
    } else {
      badge.classList.add("badge-inconclusive");
      badge.textContent = "INCONCLUSIVE";
    }

    scoreElem.textContent = data.overall_score !== null ? `${(data.overall_score * 100).toFixed(1)}%` : "N/A";
    confElem.textContent = `Confidence Margin: ${data.confidence_margin !== null ? data.confidence_margin.toFixed(2) : "0.00"}`;
    hashElem.textContent = data.file_hash || "--";
    modelElem.textContent = data.model_name || "AI PhishGuard Detector";
    facesElem.textContent = `Face Detected: ${data.face_detected ? 'Yes' : 'No'} (Count: ${data.face_count || 0})`;
    notesElem.textContent = data.uncertainty_notes || "Standard analysis executed.";

    // Update Multi-Signal Forensic Decomposition Matrix
    let elaVal = "--";
    let spectralVal = "--";
    let noiseVal = "--";
    let edgeVal = "--";

    if (data.sub_measures) {
      elaVal = data.sub_measures.ela_discontinuity != null ? `${data.sub_measures.ela_discontinuity}%` : "--";
      spectralVal = data.sub_measures.spectral_frequency != null ? `${data.sub_measures.spectral_frequency}%` : "--";
      noiseVal = data.sub_measures.noise_residual != null ? `${data.sub_measures.noise_residual}%` : "--";
      edgeVal = data.sub_measures.edge_coherence != null ? `${data.sub_measures.edge_coherence}%` : "--";
    } else if (data.uncertainty_notes) {
      const elaMatch = data.uncertainty_notes.match(/ELA Discontinuity:\s*([\d\.]+)%/);
      const specMatch = data.uncertainty_notes.match(/Spectral Frequency:\s*([\d\.]+)%/);
      const noiseMatch = data.uncertainty_notes.match(/Sensor Noise:\s*([\d\.]+)%/);
      const edgeMatch = data.uncertainty_notes.match(/Edge Coherence:\s*([\d\.]+)%/);

      if (elaMatch) elaVal = `${elaMatch[1]}%`;
      if (specMatch) spectralVal = `${specMatch[1]}%`;
      if (noiseMatch) noiseVal = `${noiseMatch[1]}%`;
      if (edgeMatch) edgeVal = `${edgeMatch[1]}%`;
    }

    const elaElem = document.getElementById("scanner-signal-ela");
    const spectralElem = document.getElementById("scanner-signal-spectral");
    const noiseElem = document.getElementById("scanner-signal-noise");
    const edgeElem = document.getElementById("scanner-signal-edge");

    if (elaElem) elaElem.textContent = elaVal;
    if (spectralElem) spectralElem.textContent = spectralVal;
    if (noiseElem) noiseElem.textContent = noiseVal;
    if (edgeElem) edgeElem.textContent = edgeVal;

    const geminiBanner = document.getElementById("scanner-gemini-banner");
    if (geminiBanner) {
      if (!data.face_detected) {
        geminiBanner.style.borderColor = "var(--accent-cyan)";
        geminiBanner.style.boxShadow = "0 0 15px rgba(0, 210, 255, 0.25)";
      } else {
        geminiBanner.style.boxShadow = "none";
      }
    }

    // Trigger dashboard update
    Dashboard.load();
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Scanner.init();
});
