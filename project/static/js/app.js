/* ── Utilities ──────────────────────────────────────────────────── */
const fmt    = n => typeof n === "number" ? n.toLocaleString("en-GB", { minimumFractionDigits:2, maximumFractionDigits:2 }) : n;
const fmtPct = v => (parseFloat(v) * 100).toFixed(1) + "%";
const isPct  = k => ["pct_instore","pct_mobile","pct_web","purchase_rate"].includes(k);

const LABELS = {
  recency:"Recency (days)", frequency:"Frequency", monetary:"Monetary (£)",
  avg_basket:"Avg Basket (£)", avg_items:"Avg Items", total_items:"Total Items",
  num_products:"Unique Products", days_active:"Days Active",
  purchase_rate:"Purchase Rate", pct_instore:"In-Store %",
  pct_mobile:"Mobile %", pct_web:"Web %"
};

/* ── Tab switching ──────────────────────────────────────────────── */
function switchTab(mode) {
  document.querySelectorAll(".tab").forEach(t => {
    t.classList.toggle("active", t.id === `tab-${mode}`);
    t.setAttribute("aria-selected", t.id === `tab-${mode}`);
  });
  document.querySelectorAll(".panel").forEach(p => {
    p.classList.toggle("active", p.id === `panel-${mode}`);
  });
  clearResults();
}
function clearResults() {
  ["result-existing","result-new","error-existing","error-new"].forEach(id => {
    document.getElementById(id)?.classList.add("hidden");
  });
}

/* ── Loading state ──────────────────────────────────────────────── */
function setLoading(btn, on) {
  btn.disabled = on;
  btn.querySelector(".btn-text").textContent = on ? "Predicting…" : "Predict Spend";
  btn.querySelector(".btn-spinner").classList.toggle("hidden", !on);
}

/* ── Feature grid ───────────────────────────────────────────────── */
function buildFeatureGrid(obj, container) {
  container.innerHTML = "";
  for (const [k, v] of Object.entries(obj)) {
    if (k === "cutoff_date") continue;
    const val   = isPct(k) ? fmtPct(v) : fmt(parseFloat(v));
    const label = LABELS[k] || k;
    container.insertAdjacentHTML("beforeend", `
      <div class="feat-item">
        <div class="feat-name">${label}</div>
        <div class="feat-value">${val}</div>
      </div>`);
  }
}

/* ── Error display ──────────────────────────────────────────────── */
function showError(el, msg) {
  el.textContent = msg;
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior:"smooth", block:"nearest" });
}

/* ── Remove error class on input ────────────────────────────────── */
document.querySelectorAll("input").forEach(i =>
  i.addEventListener("input", () => i.classList.remove("error-field"))
);

/* ════════════════════════════════════════════════════════════════
   EXISTING CUSTOMER
═══════════════════════════════════════════════════════════════ */
document.getElementById("form-existing").addEventListener("submit", async e => {
  e.preventDefault();
  const btn      = document.getElementById("btn-existing");
  const resultEl = document.getElementById("result-existing");
  const errorEl  = document.getElementById("error-existing");
  resultEl.classList.add("hidden");
  errorEl.classList.add("hidden");

  const cid    = document.getElementById("customer_id").value.trim();
  const cutoff = document.getElementById("cutoff_date_existing").value.trim();

  let valid = true;
  if (!cid)    { document.getElementById("customer_id").classList.add("error-field"); valid = false; }
  if (!cutoff) { document.getElementById("cutoff_date_existing").classList.add("error-field"); valid = false; }
  if (!valid)  { showError(errorEl, "Please fill in both Customer ID and Cutoff Date."); return; }

  setLoading(btn, true);
  try {
    const res  = await fetch("/predict/existing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id: cid, cutoff_date: cutoff })
    });
    const data = await res.json();
    if (!res.ok) { showError(errorEl, data.error || "An unexpected error occurred."); }
    else          { renderExistingResult(data); }
  } catch {
    showError(errorEl, "Network error – could not reach the server.");
  } finally {
    setLoading(btn, false);
  }
});

function renderExistingResult(data) {
  const pred = data.prediction.predicted_spend;
  document.getElementById("pred-existing-value").textContent  = fmt(pred);
  document.getElementById("pred-existing-id").textContent     = `Customer ${data.customer_id}`;
  document.getElementById("pred-existing-cutoff").textContent = `Snapshot cutoff: ${data.cutoff_date}`;

  // Actual vs predicted
  const compBlock = document.getElementById("comparison-block");
  if (data.actual !== null && data.actual !== undefined) {
    compBlock.classList.remove("hidden");
    document.getElementById("comp-predicted").textContent = `£${fmt(pred)}`;
    document.getElementById("comp-actual").textContent    = `£${fmt(data.actual)}`;
    const diff   = pred - data.actual;
    const diffEl = document.getElementById("comp-diff");
    diffEl.textContent = `${diff >= 0 ? "+" : "−"}£${fmt(Math.abs(diff))}`;
    diffEl.style.color = diff >= 0 ? "var(--cyan)" : "var(--red)";
  } else {
    compBlock.classList.add("hidden");
  }

  if (data.snapshot) buildFeatureGrid(data.snapshot, document.getElementById("snapshot-table"));

  const resultEl = document.getElementById("result-existing");
  resultEl.classList.remove("hidden");
  resultEl.scrollIntoView({ behavior:"smooth", block:"nearest" });
}

/* ════════════════════════════════════════════════════════════════
   NEW CUSTOMER – CSV Upload
═══════════════════════════════════════════════════════════════ */

// ── File input wiring ────────────────────────────────────────────
const csvInput    = document.getElementById("csv_file");
const uploadZone  = document.getElementById("upload-zone");
const uploadBody  = document.getElementById("upload-body");
const uploadSel   = document.getElementById("upload-selected");
const fileNameEl  = document.getElementById("file-name-display");
const fileClearBtn = document.getElementById("file-clear");

function showFile(name) {
  fileNameEl.textContent = name;
  uploadBody.classList.add("hidden");
  uploadSel.classList.remove("hidden");
}
function clearFile() {
  csvInput.value = "";
  uploadBody.classList.remove("hidden");
  uploadSel.classList.add("hidden");
  uploadZone.classList.remove("drag-over");
}

csvInput.addEventListener("change", () => {
  if (csvInput.files.length) showFile(csvInput.files[0].name);
});
fileClearBtn.addEventListener("click", e => { e.stopPropagation(); clearFile(); });

// Drag-and-drop
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("drag-over"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
uploadZone.addEventListener("drop", e => {
  e.preventDefault();
  uploadZone.classList.remove("drag-over");
  const files = e.dataTransfer.files;
  if (files.length) {
    // Transfer to the file input
    const dt = new DataTransfer();
    dt.items.add(files[0]);
    csvInput.files = dt.files;
    showFile(files[0].name);
  }
});

// ── Form submit ──────────────────────────────────────────────────
document.getElementById("form-new").addEventListener("submit", async e => {
  e.preventDefault();
  const btn      = document.getElementById("btn-new");
  const resultEl = document.getElementById("result-new");
  const errorEl  = document.getElementById("error-new");
  resultEl.classList.add("hidden");
  errorEl.classList.add("hidden");

  const cutoff = document.getElementById("cutoff_date_new").value.trim();
  const hasFile = csvInput.files.length > 0;

  let valid = true;
  if (!hasFile) { uploadZone.style.borderColor = "var(--red)"; valid = false; }
  if (!cutoff)  { document.getElementById("cutoff_date_new").classList.add("error-field"); valid = false; }
  if (!valid)   { showError(errorEl, "Please upload a CSV file and specify a cutoff date."); return; }
  uploadZone.style.borderColor = "";

  const formData = new FormData();
  formData.append("csv_file", csvInput.files[0]);
  formData.append("cutoff_date", cutoff);

  setLoading(btn, true);
  try {
    const res  = await fetch("/predict/new", { method:"POST", body: formData });
    const data = await res.json();
    if (!res.ok) { showError(errorEl, data.error || "An unexpected error occurred."); }
    else          { renderNewResult(data); }
  } catch {
    showError(errorEl, "Network error – could not reach the server.");
  } finally {
    setLoading(btn, false);
  }
});

function renderNewResult(data) {
  const pred = data.prediction.predicted_spend;
  document.getElementById("pred-new-value").textContent  = fmt(pred);
  document.getElementById("pred-new-cutoff").textContent = `Cutoff: ${data.cutoff_date} · 30-day forecast`;

  if (data.constructed) buildFeatureGrid(data.constructed, document.getElementById("constructed-table"));

  const resultEl = document.getElementById("result-new");
  resultEl.classList.remove("hidden");
  resultEl.scrollIntoView({ behavior:"smooth", block:"nearest" });
}
