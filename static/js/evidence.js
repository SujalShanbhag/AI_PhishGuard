// AI PhishGuard — Evidence & Visual Saliency Explorer
const EvidenceExplorer = {
  currentId: null,

  async init() {
    this.bindEvents();
    await this.populateSelector();
  },

  bindEvents() {
    const select = document.getElementById("evidence-analysis-select");
    const loadBtn = document.getElementById("btn-load-selected-evidence");
    if (loadBtn && select) {
      loadBtn.addEventListener("click", () => {
        const val = select.value;
        if (val) this.loadAnalysis(val);
      });
      select.addEventListener("change", (e) => {
        if (e.target.value) this.loadAnalysis(e.target.value);
      });
    }

    const delBtn = document.getElementById("btn-delete-evidence-analysis");
    if (delBtn) {
      delBtn.addEventListener("click", async () => {
        if (!this.currentId) return;
        if (!confirm("Are you sure you want to delete this analysis and all evidence artifacts?")) return;
        try {
          const res = await App.apiFetch(`/api/analysis/${this.currentId}`, { method: "DELETE" });
          if (res.ok) {
            App.showToast("Analysis and evidence deleted.", "success");
            this.currentId = null;
            await this.populateSelector();
            Dashboard.load();
          }
        } catch (e) {
          App.showToast("Error deleting evidence.", "danger");
        }
      });
    }

    const geminiBtn = document.getElementById("btn-evidence-gemini-audit");
    if (geminiBtn) {
      geminiBtn.addEventListener("click", () => {
        if (this.currentId && window.Copilot) {
          Copilot.inspectCurrentScanWithGemini(this.currentId);
        } else {
          App.showToast("No active scan loaded.", "info");
        }
      });
    }
  },

  async populateSelector() {
    const select = document.getElementById("evidence-analysis-select");
    if (!select) return;

    try {
      const res = await App.apiFetch("/api/analysis?limit=25");
      if (res.ok) {
        const list = await res.json();
        if (!list || list.length === 0) {
          select.innerHTML = '<option value="">No scans available</option>';
          this.showEmptyState();
          return;
        }

        select.innerHTML = list.map(item => {
          const score = item.overall_score !== null ? `${(item.overall_score * 100).toFixed(0)}%` : "N/A";
          const filename = item.filename || item.id.substring(0, 8);
          return `<option value="${item.id}">${filename} (${item.assessment} - ${score})</option>`;
        }).join("");

        // Auto-load current or first
        const targetId = this.currentId || list[0].id;
        select.value = targetId;
        await this.loadAnalysis(targetId);
      } else {
        this.showEmptyState();
      }
    } catch (e) {
      console.warn("Could not populate evidence selector:", e);
      this.showEmptyState();
    }
  },

  showEmptyState() {
    const emptyBox = document.getElementById("evidence-empty-box");
    const contentBox = document.getElementById("evidence-content-box");
    if (emptyBox) emptyBox.style.display = "block";
    if (contentBox) contentBox.style.display = "none";
  },

  async loadAnalysis(analysisId) {
    if (!analysisId) return;
    this.currentId = analysisId;

    const emptyBox = document.getElementById("evidence-empty-box");
    const contentBox = document.getElementById("evidence-content-box");
    if (emptyBox) emptyBox.style.display = "none";
    if (contentBox) contentBox.style.display = "block";

    const idLabel = document.getElementById("evidence-active-id");
    const metaSub = document.getElementById("evidence-meta-sub");
    const cropTitle = document.getElementById("evidence-crop-title");
    const faceImg = document.getElementById("evidence-face-img");
    const camImg = document.getElementById("evidence-gradcam-img");

    if (idLabel) idLabel.textContent = `Analysis ID: ${analysisId}`;

    try {
      const res = await App.apiFetch(`/api/analysis/${analysisId}`);
      if (!res.ok) throw new Error("Could not fetch analysis record");
      const data = await res.json();

      if (metaSub) {
        const faceText = data.face_detected ? `Face Isolated (${data.face_count || 1})` : "Document / Whole-Image Forensics";
        const scoreText = data.overall_score !== null ? `${(data.overall_score * 100).toFixed(1)}%` : "N/A";
        metaSub.textContent = `Mode: ${faceText} | Manipulation Score: ${scoreText} | Verdict: ${data.assessment}`;
      }

      if (cropTitle) {
        cropTitle.textContent = data.face_detected ? "Primary Face Crop (Context Preserved)" : "Salient Region of Interest (Document/Media Crop)";
      }

      await this.loadImageWithAuth(`/api/analysis/${analysisId}/evidence/face`, faceImg);
      await this.loadImageWithAuth(`/api/analysis/${analysisId}/evidence/gradcam`, camImg);
    } catch (e) {
      console.warn("Error loading evidence detail:", e);
      if (faceImg) faceImg.src = "";
      if (camImg) camImg.src = "";
    }
  },

  async loadImageWithAuth(url, imgElement) {
    if (!imgElement) return;
    try {
      const res = await App.apiFetch(url);
      if (res.ok) {
        const blob = await res.blob();
        imgElement.src = URL.createObjectURL(blob);
      } else {
        imgElement.src = "";
      }
    } catch (e) {
      imgElement.src = "";
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  EvidenceExplorer.init();
});
