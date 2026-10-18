// AI PhishGuard — Datasets Hub & Machine Learning Studio Controller
const DatasetsHub = {
  currentKey: "synthetic_10k",
  currentOffset: 0,
  pageSize: 25,
  totalRows: 0,
  searchQuery: "",
  isLoading: false,

  async init() {
    this.bindEvents();
    this.bindMLEvents();
    this.updateSplitSummary();
    await this.loadCatalog();
    await this.loadPreview(this.currentKey);
    await this.loadMLLeaderboard("real_world_phishing");
    this.renderInferenceInputs("real_world_phishing");
  },

  bindEvents() {
    // Search input
    const searchInput = document.getElementById("dataset-search-input");
    if (searchInput) {
      let debounceTimer = null;
      searchInput.addEventListener("input", (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          this.searchQuery = e.target.value.trim();
          this.currentOffset = 0;
          this.loadPreview(this.currentKey);
        }, 300);
      });
    }

    // Pagination
    const prevBtn = document.getElementById("btn-dataset-prev-page");
    const nextBtn = document.getElementById("btn-dataset-next-page");

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        if (this.currentOffset >= this.pageSize) {
          this.currentOffset -= this.pageSize;
          this.loadPreview(this.currentKey);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        if (this.currentOffset + this.pageSize < this.totalRows) {
          this.currentOffset += this.pageSize;
          this.loadPreview(this.currentKey);
        }
      });
    }

    // Custom Generator Form
    const genForm = document.getElementById("dataset-generator-form");
    if (genForm) {
      genForm.addEventListener("submit", (e) => this.handleCustomGenerate(e));
    }
  },

  updateSplitSummary() {
    const datasetSelect = document.getElementById("ml-train-dataset-select");
    const splitSlider = document.getElementById("ml-split-slider");
    const trainText = document.getElementById("ml-train-partition-text");
    const testText = document.getElementById("ml-test-partition-text");
    if (!datasetSelect || !splitSlider) return;

    const counts = {
      "real_world_phishing": 1500,
      "real_world_fraud": 1000,
      "real_world_document_forgery": 500,
      "synthetic_kyc_cyber": 10000
    };

    const key = datasetSelect.value;
    const total = counts[key] || 1500;
    const testRatio = parseInt(splitSlider.value, 10) / 100;
    const testCount = Math.round(total * testRatio);
    const trainCount = total - testCount;
    const trainRatio = Math.round((1 - testRatio) * 100);

    if (trainText) trainText.textContent = `${trainRatio}% (${trainCount.toLocaleString()} rows)`;
    if (testText) testText.textContent = `${Math.round(testRatio * 100)}% (${testCount.toLocaleString()} rows)`;
  },

  bindMLEvents() {
    // Dataset switch in ML Studio
    const datasetSelect = document.getElementById("ml-train-dataset-select");
    if (datasetSelect) {
      datasetSelect.addEventListener("change", (e) => {
        const key = e.target.value;
        this.updateSplitSummary();
        this.loadMLLeaderboard(key);
        this.renderInferenceInputs(key);
      });
    }

    // Split slider
    const splitSlider = document.getElementById("ml-split-slider");
    const splitVal = document.getElementById("ml-split-val");
    if (splitSlider && splitVal) {
      splitSlider.addEventListener("input", (e) => {
        const val = e.target.value;
        splitVal.textContent = `${val}% (${100 - val}/${val} Train/Test)`;
        this.updateSplitSummary();
      });
    }

    // Select all algorithms
    const selectAllBtn = document.getElementById("ml-select-all-algos");
    if (selectAllBtn) {
      selectAllBtn.addEventListener("click", (e) => {
        e.preventDefault();
        const boxes = document.querySelectorAll(".ml-algo-checkbox");
        const allChecked = Array.from(boxes).every(b => b.checked);
        boxes.forEach(b => b.checked = !allChecked);
        selectAllBtn.textContent = allChecked ? "Select All" : "Deselect All";
      });
    }

    // Train button
    const trainBtn = document.getElementById("btn-run-ml-training");
    if (trainBtn) {
      trainBtn.addEventListener("click", () => this.handleMLTraining());
    }

    // Test on Unseen Test Dataset buttons
    const testBtn = document.getElementById("btn-run-test-set-eval");
    if (testBtn) {
      testBtn.addEventListener("click", () => this.handleTestSetEvaluation());
    }

    const testSingleBtn = document.getElementById("btn-eval-single-test");
    if (testSingleBtn) {
      testSingleBtn.addEventListener("click", () => {
        const algoSelect = document.getElementById("ml-test-algo-select");
        const algoKey = algoSelect ? algoSelect.value : "random_forest";
        this.handleTestSetEvaluation(algoKey);
      });
    }

    // Presets
    document.querySelectorAll(".ml-preset-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const preset = btn.getAttribute("data-preset");
        this.applyMLPreset(preset);
      });
    });

    // Run prediction
    const inferBtn = document.getElementById("btn-run-live-infer");
    if (inferBtn) {
      inferBtn.addEventListener("click", () => this.handleLivePrediction());
    }
  },

  async loadCatalog() {
    try {
      const res = await App.apiFetch("/api/datasets/catalog");
      if (res.ok) {
        await res.json();
      }
    } catch (e) {
      console.warn("Could not load datasets catalog:", e);
    }
  },

  async loadPreview(datasetKey) {
    if (datasetKey !== this.currentKey) {
      this.currentKey = datasetKey;
      this.currentOffset = 0;
      const searchInput = document.getElementById("dataset-search-input");
      if (searchInput) searchInput.value = "";
      this.searchQuery = "";
    }

    const thead = document.getElementById("dataset-preview-thead");
    const tbody = document.getElementById("dataset-preview-tbody");
    const titleEl = document.getElementById("dataset-preview-title");
    const subEl = document.getElementById("dataset-preview-subtitle");

    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:var(--text-muted);"><div class="scanner-spinner" style="width:28px; height:28px; margin:0 auto 10px;"></div>Loading dataset bitstream...</td></tr>';
    }

    try {
      const q = encodeURIComponent(this.searchQuery);
      const url = `/api/datasets/preview/${this.currentKey}?limit=${this.pageSize}&offset=${this.currentOffset}&search=${q}`;
      const res = await App.apiFetch(url);
      if (!res.ok) throw new Error("Could not load dataset preview");
      const data = await res.json();

      this.totalRows = data.total_rows || 0;

      if (titleEl) titleEl.textContent = `Dataset Explorer: ${data.name} (${this.totalRows.toLocaleString()} Total Records)`;
      if (subEl) subEl.textContent = `Displaying records ${this.currentOffset + 1} to ${Math.min(this.currentOffset + this.pageSize, this.totalRows)} of ${this.totalRows.toLocaleString()} | Verified schema format`;

      const pageIndicator = document.getElementById("dataset-page-indicator");
      if (pageIndicator) {
        const currPage = Math.floor(this.currentOffset / this.pageSize) + 1;
        const maxPage = Math.ceil(this.totalRows / this.pageSize) || 1;
        pageIndicator.textContent = `Page ${currPage} / ${maxPage}`;
      }

      this.renderTable(data.columns, data.rows);
    } catch (e) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:20px; color:var(--status-danger);">Error loading dataset: ${e.message}</td></tr>`;
      }
    }
  },

  renderTable(columns, rows) {
    const thead = document.getElementById("dataset-preview-thead");
    const tbody = document.getElementById("dataset-preview-tbody");
    if (!thead || !tbody) return;

    if (!columns || columns.length === 0) {
      thead.innerHTML = "<tr><th>Empty Schema</th></tr>";
      tbody.innerHTML = "<tr><td>No records present.</td></tr>";
      return;
    }

    // Render Headers
    thead.innerHTML = `<tr>${columns.map(c => `<th>${c.replace(/_/g, ' ').toUpperCase()}</th>`).join('')}</tr>`;

    // Render Rows
    if (!rows || rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="${columns.length}" style="text-align:center; color:var(--text-muted); padding:20px;">No matching records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map((r) => {
      return `
        <tr>
          ${columns.map(c => {
            let val = r[c];
            if (val === null || val === undefined) val = '--';
            if (c === "is_phishing" || c === "fraud_flag" || c === "is_fraud_flag") {
              const isBad = String(val).toUpperCase().includes("PHISH") || val === 1 || String(val).toUpperCase().includes("FRAUD");
              const badgeClass = isBad ? "badge-suspicious" : "badge-clean";
              return `<td><span class="badge ${badgeClass}" style="font-size:10.5px;">${val}</span></td>`;
            }
            if (c === "aadhar_no") {
              return `<td style="font-family:var(--font-mono); color:var(--accent-cyan); font-weight:600;">${val}</td>`;
            }
            return `<td style="white-space:nowrap; font-size:11.5px;">${String(val).substring(0, 35)}</td>`;
          }).join('')}
        </tr>
      `;
    }).join('');
  },

  async handleCustomGenerate(e) {
    e.preventDefault();
    const rows = parseInt(document.getElementById("gen-dataset-rows").value, 10) || 500;
    const format = document.getElementById("gen-dataset-format").value || "csv";
    const extended = document.getElementById("gen-extended-cols").checked;
    const btn = document.getElementById("btn-generate-dataset");

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<div class="scanner-spinner" style="width:14px; height:14px; display:inline-block; vertical-align:middle; margin-right:8px;"></div> Synthesizing ${rows.toLocaleString()} Records...`;

    try {
      const res = await App.apiFetch("/api/datasets/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rows: rows,
          format: format,
          extended_columns: extended
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Generation failed.");
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `synthetic_kyc_dataset_${rows}rows.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      App.showToast(`Generated & downloaded ${rows.toLocaleString()} records in ${format.toUpperCase()} format!`, "success");
    } catch (err) {
      App.showToast(`Generation error: ${err.message}`, "danger");
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  },

  // =========================================================================
  // MACHINE LEARNING MODEL TRAINING & BENCHMARK STUDIO
  // =========================================================================
  async loadMLLeaderboard(datasetKey) {
    const tbody = document.getElementById("ml-leaderboard-tbody");
    if (!tbody) return;

    try {
      const res = await App.apiFetch(`/api/ml/leaderboard?dataset_key=${encodeURIComponent(datasetKey)}`);
      if (res.ok) {
        const data = await res.json();
        this.renderMLLeaderboard(data.leaderboard);
        if (data.leaderboard && data.leaderboard.length > 0 && data.leaderboard[0].test_samples) {
          const topModel = data.leaderboard[0];
          this.renderTestEvaluation({
            algorithm: topModel.name,
            dataset: datasetKey,
            test_accuracy: topModel.accuracy,
            precision: topModel.precision,
            recall: topModel.recall,
            f1_score: topModel.f1_score,
            roc_auc: topModel.roc_auc,
            test_samples_count: topModel.test_samples.length,
            test_samples: topModel.test_samples
          });
        }
      }
    } catch (e) {
      console.warn("Could not load ML leaderboard:", e);
    }
  },

  renderMLLeaderboard(leaderboard) {
    const tbody = document.getElementById("ml-leaderboard-tbody");
    const bestBadge = document.getElementById("ml-best-badge");
    if (!tbody) return;

    if (!leaderboard || leaderboard.length === 0) {
      tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; color:var(--text-muted); padding:20px;">Click "Train Selected ML Models" or "Test on Unseen Test Dataset" to benchmark algorithms.</td></tr>';
      if (bestBadge) bestBadge.style.display = "none";
      return;
    }

    if (bestBadge) {
      bestBadge.style.display = "inline-block";
      bestBadge.textContent = `Top Performer: ${leaderboard[0].name} (Test F1: ${leaderboard[0].f1_score}%)`;
    }

    tbody.innerHTML = leaderboard.map((m, idx) => {
      const isTop = idx === 0;
      const rankBadge = isTop ? '🥇 1' : (idx === 1 ? '🥈 2' : (idx === 2 ? '🥉 3' : `#${idx + 1}`));
      const rowHighlight = isTop ? 'style="background:rgba(0, 210, 255, 0.08); font-weight:600;"' : '';
      const trainAcc = m.train_accuracy !== undefined ? `${m.train_accuracy.toFixed(1)}%` : '—';
      const testAcc = m.accuracy !== undefined ? `${m.accuracy.toFixed(1)}%` : '—';

      return `
        <tr ${rowHighlight}>
          <td>${rankBadge}</td>
          <td style="color:var(--text-primary); font-weight:600;">${m.name}</td>
          <td><span style="font-size:11px; color:var(--text-secondary);">${m.family || 'ML'}</span></td>
          <td style="font-family:var(--font-mono); color:var(--accent-cyan);">${trainAcc}</td>
          <td style="font-family:var(--font-mono); color:var(--status-warning); font-weight:700;">${testAcc}</td>
          <td style="font-family:var(--font-mono);">${m.precision.toFixed(1)}%</td>
          <td style="font-family:var(--font-mono);">${m.recall.toFixed(1)}%</td>
          <td style="font-family:var(--font-mono); color:var(--status-success); font-weight:700;">${m.f1_score.toFixed(1)}%</td>
          <td style="font-family:var(--font-mono);">${m.roc_auc ? m.roc_auc.toFixed(1) + '%' : 'N/A'}</td>
          <td style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${m.train_time_ms} ms</td>
          <td>
            <button class="btn btn-secondary" onclick="DatasetsHub.handleTestSetEvaluation('${m.algorithm_key}')" style="font-size:10.5px; padding:3px 8px;" title="Evaluate this algorithm on test partition">
              🧪 Test
            </button>
          </td>
        </tr>
      `;
    }).join('');
  },

  async handleMLTraining() {
    const datasetSelect = document.getElementById("ml-train-dataset-select");
    const splitSlider = document.getElementById("ml-split-slider");
    const spinner = document.getElementById("ml-training-spinner");
    const spinnerText = document.getElementById("ml-spinner-text");
    const trainBtn = document.getElementById("btn-run-ml-training");

    const datasetKey = datasetSelect ? datasetSelect.value : "real_world_phishing";
    const testSplit = splitSlider ? parseInt(splitSlider.value, 10) / 100 : 0.20;

    const checkedBoxes = Array.from(document.querySelectorAll(".ml-algo-checkbox:checked"));
    const selectedAlgos = checkedBoxes.map(b => b.value);

    if (selectedAlgos.length === 0) {
      App.showToast("Please select at least one algorithm to train.", "warning");
      return;
    }

    if (spinnerText) spinnerText.textContent = "Training models on Train Set & validating on Test Set...";
    if (spinner) spinner.style.display = "inline-flex";
    if (trainBtn) trainBtn.disabled = true;

    try {
      const res = await App.apiFetch("/api/ml/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_key: datasetKey,
          algorithms: selectedAlgos,
          test_size: testSplit
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Training failed");
      }

      const data = await res.json();
      this.renderMLLeaderboard(data.leaderboard);

      if (data.leaderboard && data.leaderboard.length > 0) {
        const top = data.leaderboard[0];
        if (top.test_samples) {
          this.renderTestEvaluation({
            algorithm: top.name,
            dataset: datasetKey,
            test_accuracy: top.accuracy,
            precision: top.precision,
            recall: top.recall,
            f1_score: top.f1_score,
            roc_auc: top.roc_auc,
            test_samples_count: top.test_samples.length,
            test_samples: top.test_samples
          });
        }
      }

      App.showToast(`Trained ${data.models_evaluated} ML models on Train Set (${data.train_samples} rows)! Validated on ${data.test_samples} unseen test rows. Best model: ${data.best_model}`, "success");
    } catch (e) {
      App.showToast(`Training error: ${e.message}`, "danger");
    } finally {
      if (spinner) spinner.style.display = "none";
      if (trainBtn) trainBtn.disabled = false;
    }
  },

  async handleTestSetEvaluation(algoKey = null) {
    const datasetSelect = document.getElementById("ml-train-dataset-select");
    const algoSelect = document.getElementById("ml-test-algo-select");
    const splitSlider = document.getElementById("ml-split-slider");
    const spinner = document.getElementById("ml-training-spinner");
    const spinnerText = document.getElementById("ml-spinner-text");
    const testBtn = document.getElementById("btn-run-test-set-eval");

    const datasetKey = datasetSelect ? datasetSelect.value : "real_world_phishing";
    const algorithmKey = algoKey || (algoSelect ? algoSelect.value : "random_forest");
    const testSplit = splitSlider ? parseInt(splitSlider.value, 10) / 100 : 0.20;

    if (algoSelect && algoKey) {
      algoSelect.value = algoKey;
    }

    if (spinnerText) spinnerText.textContent = `Evaluating ${algorithmKey} on unseen test partition...`;
    if (spinner) spinner.style.display = "inline-flex";
    if (testBtn) testBtn.disabled = true;

    try {
      const res = await App.apiFetch("/api/ml/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_key: datasetKey,
          algorithm_key: algorithmKey,
          test_size: testSplit
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Test evaluation failed");
      }

      const data = await res.json();
      this.renderTestEvaluation(data);
      App.showToast(`Test evaluation complete for ${data.algorithm}: ${data.test_accuracy}% accuracy on unseen records!`, "success");
    } catch (e) {
      App.showToast(`Test evaluation error: ${e.message}`, "danger");
    } finally {
      if (spinner) spinner.style.display = "none";
      if (testBtn) testBtn.disabled = false;
    }
  },

  renderTestEvaluation(data) {
    const accEl = document.getElementById("ml-stat-test-acc");
    const precEl = document.getElementById("ml-stat-test-prec");
    const recEl = document.getElementById("ml-stat-test-rec");
    const f1El = document.getElementById("ml-stat-test-f1");
    const aucEl = document.getElementById("ml-stat-test-auc");
    const countBadge = document.getElementById("ml-test-count-badge");
    const tbody = document.getElementById("ml-test-samples-tbody");

    if (accEl) accEl.textContent = `${data.test_accuracy}%`;
    if (precEl) precEl.textContent = `${data.precision}%`;
    if (recEl) recEl.textContent = `${data.recall}%`;
    if (f1El) f1El.textContent = `${data.f1_score}%`;
    if (aucEl) aucEl.textContent = data.roc_auc ? `${data.roc_auc}%` : 'N/A';
    if (countBadge) countBadge.textContent = `${data.algorithm || 'Model'} • ${data.test_samples_count || (data.test_samples ? data.test_samples.length : 0)} Test Rows`;

    if (!tbody) return;

    const samples = data.test_samples || [];
    if (samples.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:16px;">No test samples returned for this model.</td></tr>';
      return;
    }

    tbody.innerHTML = samples.map(s => {
      const isMatch = s.is_correct;
      const matchPill = isMatch
        ? '<span class="badge badge-clean" style="font-size:10px;">✅ MATCH</span>'
        : '<span class="badge badge-suspicious" style="font-size:10px;">⚠️ MISMATCH</span>';

      const isThreat = String(s.ground_truth).toUpperCase().includes("THREAT") || String(s.ground_truth).toUpperCase().includes("TAMPERED") || String(s.ground_truth).toUpperCase().includes("FRAUD");
      const gtBadge = isThreat
        ? '<span class="badge badge-danger" style="font-size:10px;">THREAT</span>'
        : '<span class="badge badge-clean" style="font-size:10px;">CLEAN</span>';

      const isPredThreat = String(s.predicted).toUpperCase().includes("THREAT") || String(s.predicted).toUpperCase().includes("TAMPERED") || String(s.predicted).toUpperCase().includes("FRAUD");
      const predBadge = isPredThreat
        ? '<span class="badge badge-danger" style="font-size:10px;">THREAT</span>'
        : '<span class="badge badge-clean" style="font-size:10px;">CLEAN</span>';

      const featurePreview = Object.entries(s.features || {})
        .slice(0, 3)
        .map(([k, v]) => `<span style="color:var(--text-muted); font-size:10px;">${k}:</span> <strong style="color:var(--text-primary); font-size:10.5px;">${typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(2)) : v}</strong>`)
        .join(' • ');

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-cyan); font-size:11px;">${s.sample_id}</td>
          <td style="font-size:11px; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${featurePreview}</td>
          <td>${gtBadge} <span style="font-size:11px; color:var(--text-secondary); margin-left:4px;">${s.ground_truth}</span></td>
          <td>${predBadge} <span style="font-size:11px; color:var(--text-secondary); margin-left:4px;">${s.predicted}</span></td>
          <td style="font-family:var(--font-mono); font-weight:600; color:var(--text-primary); font-size:11px;">${s.confidence_score}%</td>
          <td>${matchPill}</td>
        </tr>
      `;
    }).join('');
  },

  renderInferenceInputs(datasetKey) {
    const container = document.getElementById("ml-inference-inputs");
    if (!container) return;

    if (datasetKey === "real_world_phishing") {
      container.innerHTML = `
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">URL Character Length</label>
          <input type="number" id="inf-url-len" class="form-input" value="78" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Dot Count (.)</label>
          <input type="number" id="inf-dots" class="form-input" value="3" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Character Entropy</label>
          <input type="number" step="0.1" id="inf-entropy" class="form-input" value="4.8" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Subdomain Count</label>
          <input type="number" id="inf-subdomains" class="form-input" value="2" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Phishing Keywords Found</label>
          <input type="number" id="inf-keywords" class="form-input" value="2" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Uses HTTPS (1=Yes, 0=No)</label>
          <input type="number" id="inf-https" class="form-input" value="0" style="padding:4px 8px; font-size:12px;">
        </div>
      `;
    } else if (datasetKey === "real_world_fraud") {
      container.innerHTML = `
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Transfer Amount (INR)</label>
          <input type="number" id="inf-amount" class="form-input" value="950000" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Channel (1=UPI, 2=NEFT, 3=IMPS)</label>
          <input type="number" id="inf-channel" class="form-input" value="3" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Old Account Balance (INR)</label>
          <input type="number" id="inf-old-bal" class="form-input" value="980000" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">New Account Balance (INR)</label>
          <input type="number" id="inf-new-bal" class="form-input" value="30000" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">High Risk Country Flag (1/0)</label>
          <input type="number" id="inf-country-risk" class="form-input" value="1" style="padding:4px 8px; font-size:12px;">
        </div>
      `;
    } else if (datasetKey === "real_world_document_forgery") {
      container.innerHTML = `
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Mean ELA Error Level (0-255)</label>
          <input type="number" step="0.1" id="inf-ela-mean" class="form-input" value="34.8" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Max Differential Error (0-255)</label>
          <input type="number" step="0.1" id="inf-ela-max" class="form-input" value="188.0" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Error Level Variance</label>
          <input type="number" step="0.1" id="inf-ela-var" class="form-input" value="412.5" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Surface Laplacian Sharpness</label>
          <input type="number" step="0.1" id="inf-laplacian" class="form-input" value="128.4" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Tampering Confidence (0.0-1.0)</label>
          <input type="number" step="0.05" id="inf-tamper-conf" class="form-input" value="0.85" style="padding:4px 8px; font-size:12px;">
        </div>
      `;
    } else {
      container.innerHTML = `
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Applicant Age</label>
          <input type="number" id="inf-age" class="form-input" value="32" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Credit Score (300-900)</label>
          <input type="number" id="inf-credit" class="form-input" value="510" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">Cyber Risk Score (0-100)</label>
          <input type="number" id="inf-risk" class="form-input" value="84" style="padding:4px 8px; font-size:12px;">
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <label style="font-size:11px; color:var(--text-secondary);">MFA Enabled (1=Yes, 0=No)</label>
          <input type="number" id="inf-mfa" class="form-input" value="0" style="padding:4px 8px; font-size:12px;">
        </div>
      `;
    }
  },

  applyMLPreset(presetName) {
    const datasetSelect = document.getElementById("ml-train-dataset-select");
    if (!datasetSelect) return;

    if (presetName === "phish-google") {
      datasetSelect.value = "real_world_phishing";
      this.updateSplitSummary();
      this.renderInferenceInputs("real_world_phishing");
      setTimeout(() => {
        const len = document.getElementById("inf-url-len");
        const dots = document.getElementById("inf-dots");
        const ent = document.getElementById("inf-entropy");
        const kw = document.getElementById("inf-keywords");
        const https = document.getElementById("inf-https");
        if (len) len.value = "94";
        if (dots) dots.value = "4";
        if (ent) ent.value = "5.2";
        if (kw) kw.value = "3";
        if (https) https.value = "0";
      }, 50);
    } else if (presetName === "clean-gov") {
      datasetSelect.value = "real_world_phishing";
      this.updateSplitSummary();
      this.renderInferenceInputs("real_world_phishing");
      setTimeout(() => {
        const len = document.getElementById("inf-url-len");
        const dots = document.getElementById("inf-dots");
        const ent = document.getElementById("inf-entropy");
        const kw = document.getElementById("inf-keywords");
        const https = document.getElementById("inf-https");
        if (len) len.value = "24";
        if (dots) dots.value = "2";
        if (ent) ent.value = "3.2";
        if (kw) kw.value = "0";
        if (https) https.value = "1";
      }, 50);
    } else if (presetName === "fraud-tx") {
      datasetSelect.value = "real_world_fraud";
      this.updateSplitSummary();
      this.renderInferenceInputs("real_world_fraud");
      setTimeout(() => {
        const amt = document.getElementById("inf-amount");
        const risk = document.getElementById("inf-country-risk");
        if (amt) amt.value = "1450000";
        if (risk) risk.value = "1";
      }, 50);
    } else if (presetName === "clean-upi") {
      datasetSelect.value = "real_world_fraud";
      this.updateSplitSummary();
      this.renderInferenceInputs("real_world_fraud");
      setTimeout(() => {
        const amt = document.getElementById("inf-amount");
        const risk = document.getElementById("inf-country-risk");
        if (amt) amt.value = "2400";
        if (risk) risk.value = "0";
      }, 50);
    } else if (presetName === "forgery-doc") {
      datasetSelect.value = "real_world_document_forgery";
      this.updateSplitSummary();
      this.renderInferenceInputs("real_world_document_forgery");
      setTimeout(() => {
        const mean = document.getElementById("inf-ela-mean");
        const max = document.getElementById("inf-ela-max");
        const varEl = document.getElementById("inf-ela-var");
        const lap = document.getElementById("inf-laplacian");
        const conf = document.getElementById("inf-tamper-conf");
        if (mean) mean.value = "48.5";
        if (max) max.value = "220.0";
        if (varEl) varEl.value = "540.0";
        if (lap) lap.value = "95.0";
        if (conf) conf.value = "0.92";
      }, 50);
    } else if (presetName === "clean-doc") {
      datasetSelect.value = "real_world_document_forgery";
      this.updateSplitSummary();
      this.renderInferenceInputs("real_world_document_forgery");
      setTimeout(() => {
        const mean = document.getElementById("inf-ela-mean");
        const max = document.getElementById("inf-ela-max");
        const varEl = document.getElementById("inf-ela-var");
        const lap = document.getElementById("inf-laplacian");
        const conf = document.getElementById("inf-tamper-conf");
        if (mean) mean.value = "4.2";
        if (max) max.value = "18.0";
        if (varEl) varEl.value = "22.0";
        if (lap) lap.value = "165.0";
        if (conf) conf.value = "0.08";
      }, 50);
    }
  },

  async handleLivePrediction() {
    const datasetSelect = document.getElementById("ml-train-dataset-select");
    const datasetKey = datasetSelect ? datasetSelect.value : "real_world_phishing";
    const verdictEl = document.getElementById("ml-result-verdict");
    const probEl = document.getElementById("ml-result-prob");

    if (verdictEl) verdictEl.innerHTML = '<div class="scanner-spinner" style="width:18px; height:18px; margin:0 auto;"></div>';

    let inputData = {};
    if (datasetKey === "real_world_phishing") {
      inputData = {
        url_length: parseFloat(document.getElementById("inf-url-len")?.value || 50),
        count_dots: parseFloat(document.getElementById("inf-dots")?.value || 2),
        count_hyphens: 1,
        count_slashes: 2,
        has_at_symbol: 0,
        uses_https_ssl: parseFloat(document.getElementById("inf-https")?.value || 0),
        ip_address_in_host: 0,
        character_entropy: parseFloat(document.getElementById("inf-entropy")?.value || 4.0),
        subdomain_count: parseFloat(document.getElementById("inf-subdomains")?.value || 1),
        phishing_keywords_found: parseFloat(document.getElementById("inf-keywords")?.value || 0)
      };
    } else if (datasetKey === "real_world_fraud") {
      inputData = {
        amount_inr: parseFloat(document.getElementById("inf-amount")?.value || 10000),
        channel_encoded: parseFloat(document.getElementById("inf-channel")?.value || 1),
        old_balance_orig: parseFloat(document.getElementById("inf-old-bal")?.value || 100000),
        new_balance_orig: parseFloat(document.getElementById("inf-new-bal")?.value || 90000),
        is_high_risk_country: parseFloat(document.getElementById("inf-country-risk")?.value || 0)
      };
    } else if (datasetKey === "real_world_document_forgery") {
      inputData = {
        mean_ela_error: parseFloat(document.getElementById("inf-ela-mean")?.value || 30.0),
        max_differential_error: parseFloat(document.getElementById("inf-ela-max")?.value || 150.0),
        error_level_variance: parseFloat(document.getElementById("inf-ela-var")?.value || 300.0),
        surface_laplacian_sharpness: parseFloat(document.getElementById("inf-laplacian")?.value || 120.0),
        tampering_confidence: parseFloat(document.getElementById("inf-tamper-conf")?.value || 0.8)
      };
    } else {
      inputData = {
        age: parseFloat(document.getElementById("inf-age")?.value || 30),
        annual_income_inr: 800000,
        credit_score: parseFloat(document.getElementById("inf-credit")?.value || 650),
        cyber_risk_score: parseFloat(document.getElementById("inf-risk")?.value || 40),
        mfa_num: parseFloat(document.getElementById("inf-mfa")?.value || 1),
        gender_num: 0
      };
    }

    try {
      const res = await App.apiFetch("/api/ml/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_key: datasetKey,
          algorithm_key: "random_forest",
          input_data: inputData
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Prediction request failed");
      }

      const data = await res.json();
      const isThreat = data.prediction === 1;
      const badgeColor = isThreat ? "var(--status-danger)" : "var(--status-success)";

      if (verdictEl) {
        verdictEl.style.color = badgeColor;
        verdictEl.textContent = `${isThreat ? '🚨' : '✅'} ${data.verdict}`;
      }

      if (probEl) {
        const probText = data.probability !== null ? `Threat Probability: ${data.probability}%` : `Risk Tier: ${data.risk_tier}`;
        probEl.textContent = `${probText} • Model: ${data.algorithm}`;
      }
    } catch (e) {
      if (verdictEl) {
        verdictEl.style.color = "var(--status-danger)";
        verdictEl.textContent = "Prediction Error";
      }
      if (probEl) probEl.textContent = e.message;
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  DatasetsHub.init();
});
