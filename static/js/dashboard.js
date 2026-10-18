const Dashboard = {
  chartInstance: null,

  async load() {
    try {
      const res = await App.apiFetch("/api/analysis/history");
      if (!res.ok) return;
      const records = await res.json();
      this.updateMetrics(records);
      this.updateRecentTable(records);
      this.updateChart(records);
    } catch (e) {
      console.error("Dashboard load failed", e);
    }
  },

  updateMetrics(records) {
    const total = records.length;
    let suspicious = 0;
    let clean = 0;
    let inconclusive = 0;

    records.forEach(r => {
      if (r.assessment === "POTENTIALLY_SUSPICIOUS") suspicious++;
      else if (r.assessment === "NO_STRONG_EVIDENCE") clean++;
      else inconclusive++;
    });

    document.getElementById("stat-total-scans").textContent = total;
    document.getElementById("stat-suspicious").textContent = suspicious;
    document.getElementById("stat-clean").textContent = clean;
    document.getElementById("stat-inconclusive").textContent = inconclusive;
  },

  updateRecentTable(records) {
    const tbody = document.getElementById("overview-recent-table");
    if (!tbody) return;

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No forensic analyses recorded yet.</td></tr>`;
      return;
    }

    const recent = records.slice(0, 5);
    tbody.innerHTML = recent.map(r => {
      const badgeClass = r.assessment === "POTENTIALLY_SUSPICIOUS" ? "badge-suspicious" : (
        r.assessment === "NO_STRONG_EVIDENCE" ? "badge-clean" : "badge-inconclusive"
      );
      const shortHash = r.file_hash ? `${r.file_hash.substring(0, 8)}...` : "N/A";
      const dateStr = new Date(r.created_at).toLocaleDateString();

      return `
        <tr>
          <td><strong>${r.original_filename}</strong></td>
          <td><span class="format-pill">${r.media_type}</span></td>
          <td><code style="font-size:11px; color:var(--accent-cyan);">${shortHash}</code></td>
          <td><span class="badge ${badgeClass}">${r.assessment.replace(/_/g, ' ')}</span></td>
          <td style="color:var(--text-muted); font-size:12px;">${dateStr}</td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-secondary" onclick="EvidenceExplorer.loadAnalysis('${r.id}')" style="padding:2px 8px; font-size:11px;">Inspect</button>
              <button class="btn btn-primary" onclick="Copilot.inspectCurrentScanWithGemini('${r.id}')" style="padding:2px 8px; font-size:11px;">✨ Audit</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  },

  updateChart(records) {
    const ctx = document.getElementById("overview-pie-chart");
    if (!ctx) return;

    let suspicious = 0, clean = 0, inconclusive = 0;
    records.forEach(r => {
      if (r.assessment === "POTENTIALLY_SUSPICIOUS") suspicious++;
      else if (r.assessment === "NO_STRONG_EVIDENCE") clean++;
      else inconclusive++;
    });

    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    this.chartInstance = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Suspicious", "No Strong Evidence", "Inconclusive"],
        datasets: [{
          data: [suspicious, clean, inconclusive],
          backgroundColor: ["#ef4444", "#10b981", "#f59e0b"],
          borderColor: "#0d1527",
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", font: { size: 11 } }
          }
        }
      }
    });
  },

  async loadHistory() {
    const tbody = document.getElementById("history-table-body");
    if (!tbody) return;

    try {
      const res = await App.apiFetch("/api/analysis/history");
      const records = await res.json();

      if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No records found.</td></tr>`;
        return;
      }

      tbody.innerHTML = records.map(r => {
        const badgeClass = r.assessment === "POTENTIALLY_SUSPICIOUS" ? "badge-suspicious" : (
          r.assessment === "NO_STRONG_EVIDENCE" ? "badge-clean" : "badge-inconclusive"
        );
        const scoreStr = r.overall_score !== null ? `${(r.overall_score * 100).toFixed(1)}%` : "N/A";

        return `
          <tr>
            <td><code style="font-size:11px; color:var(--accent-cyan);">${r.id.substring(0, 8)}</code></td>
            <td><strong>${r.original_filename}</strong></td>
            <td><span class="format-pill">${r.media_type}</span></td>
            <td><code style="font-size:11px;" title="${r.file_hash}">${r.file_hash.substring(0, 12)}...</code></td>
            <td><span class="badge ${badgeClass}">${r.assessment.replace(/_/g, ' ')}</span></td>
            <td style="font-family:var(--font-mono); font-weight:600;">${scoreStr}</td>
            <td>
              <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="EvidenceExplorer.loadAnalysis('${r.id}')">Inspect</button>
              <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="Dashboard.quickGenerateReport('${r.id}')">Report</button>
              <button class="btn btn-danger" style="padding:4px 8px; font-size:11px;" onclick="Dashboard.deleteAnalysis('${r.id}')">Delete</button>
            </td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      console.error(e);
    }
  },

  async loadReports() {
    const tbody = document.getElementById("reports-table-body");
    if (!tbody) return;

    try {
      const res = await App.apiFetch("/api/analysis/history");
      const records = await res.json();

      tbody.innerHTML = records.map(r => {
        const badgeClass = r.assessment === "POTENTIALLY_SUSPICIOUS" ? "badge-suspicious" : (
          r.assessment === "NO_STRONG_EVIDENCE" ? "badge-clean" : "badge-inconclusive"
        );
        const dateStr = new Date(r.created_at).toLocaleDateString();

        return `
          <tr>
            <td><code style="color:var(--accent-cyan);">${r.id.substring(0, 8)}</code></td>
            <td><strong>${r.original_filename}</strong></td>
            <td>${dateStr}</td>
            <td><span class="badge ${badgeClass}">${r.assessment.replace(/_/g, ' ')}</span></td>
            <td>
              <button class="btn btn-primary" style="padding:5px 12px; font-size:12px;" onclick="Dashboard.quickGenerateReport('${r.id}')">Download PDF</button>
              <button class="btn btn-danger" style="padding:5px 10px; font-size:12px;" onclick="Dashboard.deleteAnalysis('${r.id}')">Delete</button>
            </td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      console.error(e);
    }
  },

  async deleteAnalysis(analysisId) {
    if (!confirm("Are you sure you want to permanently delete this analysis and all uploaded media?")) return;
    try {
      const res = await App.apiFetch(`/api/analysis/${analysisId}`, { method: "DELETE" });
      if (res.ok) {
        App.showToast("Analysis and uploaded file deleted successfully.", "success");
        this.load();
        this.loadHistory();
        this.loadReports();
      } else {
        App.showToast("Failed to delete analysis.", "danger");
      }
    } catch (e) {
      App.showToast("Error deleting analysis.", "danger");
    }
  },

  async purgeAll() {
    if (!confirm("CAUTION: This will permanently delete ALL uploaded media files and analysis records for your account. Continue?")) return;
    try {
      const res = await App.apiFetch("/api/analysis/all", { method: "DELETE" });
      if (res.ok) {
        const data = await res.json();
        App.showToast(data.message || "All uploads purged successfully.", "success");
        this.load();
        this.loadHistory();
        this.loadReports();
      } else {
        App.showToast("Failed to purge uploads.", "danger");
      }
    } catch (e) {
      App.showToast("Error purging uploads.", "danger");
    }
  },

  async quickGenerateReport(analysisId) {
    App.showToast("Generating forensic PDF report...", "info");
    try {
      const res = await App.apiFetch(`/api/reports/${analysisId}/generate`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        window.open(data.download_url, "_blank");
        App.showToast("Report compiled successfully.", "success");
      } else {
        App.showToast("Report compilation failed.", "danger");
      }
    } catch (e) {
      App.showToast("Network error generating report.", "danger");
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const purgeBtn = document.getElementById("btn-purge-all-history");
  if (purgeBtn) {
    purgeBtn.addEventListener("click", () => Dashboard.purgeAll());
  }
});
