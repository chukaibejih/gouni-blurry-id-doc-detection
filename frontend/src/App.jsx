import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:8000";

const GRADE_COLORS = {
  Good:     { bg: "#d1fae5", text: "#065f46", border: "#6ee7b7" },
  Mild:     { bg: "#fef9c3", text: "#713f12", border: "#fde047" },
  Moderate: { bg: "#fed7aa", text: "#7c2d12", border: "#fb923c" },
  Severe:   { bg: "#fee2e2", text: "#7f1d1d", border: "#fca5a5" },
};

function ScoreBar({ score }) {
  const color = score >= 75 ? "#16a34a" : score >= 50 ? "#ca8a04" : score >= 25 ? "#ea580c" : "#dc2626";
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#6b7280", marginBottom: 4 }}>
        <span>Blur Score</span><span style={{ fontWeight: 700, color }}>{score}/100</span>
      </div>
      <div style={{ background: "#e5e7eb", borderRadius: 8, height: 10, overflow: "hidden" }}>
        <div style={{ width: `${score}%`, background: color, height: "100%", borderRadius: 8, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

function ProcessLog({ steps }) {
  if (!steps?.length) return null;

  return (
    <div style={{ marginTop: 16, background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8, padding: "12px 14px" }}>
      <p style={{ margin: "0 0 10px", fontWeight: 700, fontSize: 13, color: "#374151" }}>Processing log</p>
      <ol style={{ margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 1.55, color: "#4b5563" }}>
        {steps.map((step, index) => (
          <li key={`${index}-${step}`} style={{ marginBottom: index === steps.length - 1 ? 0 : 6 }}>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}

function UploadPage() {
  const [file, setFile]       = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [dragging, setDragging] = useState(false);

  const handleFile = (f) => {
    if (!f) return;
    if (!["image/jpeg", "image/jpg", "image/png"].includes(f.type)) {
      setError("Only JPEG and PNG files are accepted.");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("File size must not exceed 10MB.");
      return;
    }
    setError("");
    setResult(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await axios.post(`${API}/api/upload`, form);
      console.groupCollapsed(`Blur analysis: ${file.name}`);
      console.table(res.data.process_log || []);
      console.groupEnd();
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null); setPreview(null); setResult(null); setError("");
  };

  const gradeStyle = result ? GRADE_COLORS[result.grade] || {} : {};
  const accepted   = result?.decision === "accepted";

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      <div style={{ background: "#fff", borderRadius: 12, boxShadow: "0 2px 16px rgba(0,0,0,0.08)", padding: 32 }}>
        <h2 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: "#111827" }}>Upload Identity Document</h2>
        <p style={{ margin: "0 0 24px", fontSize: 14, color: "#6b7280" }}>
          Supported formats: JPEG, PNG &nbsp;·&nbsp; Max size: 10MB
        </p>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById("fileInput").click()}
          style={{
            border: `2px dashed ${dragging ? "#2563eb" : "#d1d5db"}`,
            borderRadius: 10,
            padding: "32px 16px",
            textAlign: "center",
            cursor: "pointer",
            background: dragging ? "#eff6ff" : "#f9fafb",
            transition: "all 0.2s",
            marginBottom: 16,
          }}
        >
          {preview ? (
            <img src={preview} alt="preview" style={{ maxHeight: 180, maxWidth: "100%", borderRadius: 6, objectFit: "contain" }} />
          ) : (
            <>
              <div style={{ fontSize: 40, marginBottom: 8 }}>📄</div>
              <p style={{ margin: 0, fontWeight: 600, color: "#374151" }}>Drag & drop or click to select</p>
              <p style={{ margin: "4px 0 0", fontSize: 13, color: "#9ca3af" }}>Identity document image (passport, ID card, driver's licence)</p>
            </>
          )}
          <input id="fileInput" type="file" accept="image/jpeg,image/png" style={{ display: "none" }}
            onChange={(e) => handleFile(e.target.files[0])} />
        </div>

        {file && (
          <p style={{ fontSize: 13, color: "#6b7280", margin: "0 0 16px" }}>
            Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
          </p>
        )}

        {error && (
          <div style={{ background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 14px", color: "#7f1d1d", fontSize: 14, marginBottom: 16 }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={handleSubmit} disabled={!file || loading}
            style={{
              flex: 1, padding: "12px 0", borderRadius: 8, border: "none",
              background: !file || loading ? "#d1d5db" : "#1d4ed8",
              color: !file || loading ? "#9ca3af" : "#fff",
              fontWeight: 700, fontSize: 15, cursor: !file || loading ? "not-allowed" : "pointer",
              transition: "background 0.2s"
            }}>
            {loading ? "Analysing..." : "Submit for Blur Analysis"}
          </button>
          {(file || result) && (
            <button onClick={reset} style={{ padding: "12px 18px", borderRadius: 8, border: "1px solid #d1d5db", background: "#fff", color: "#374151", fontWeight: 600, cursor: "pointer" }}>
              Reset
            </button>
          )}
        </div>

        {/* Result panel */}
        {result && (
          <div style={{
            marginTop: 24, borderRadius: 10, border: `1px solid ${accepted ? "#6ee7b7" : "#fca5a5"}`,
            background: accepted ? "#f0fdf4" : "#fff1f2", padding: 20,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <span style={{ fontSize: 28 }}>{accepted ? "✅" : "❌"}</span>
              <div>
                <p style={{ margin: 0, fontWeight: 700, fontSize: 16, color: accepted ? "#065f46" : "#7f1d1d" }}>
                  {accepted ? "Image Accepted" : "Image Rejected"}
                </p>
                <p style={{ margin: 0, fontSize: 13, color: "#6b7280" }}>{result.file_name}</p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 16 }}>
              {[
                { label: "Composite Score", value: `${result.composite_score}` },
                { label: "Laplacian", value: result.laplacian_score.toFixed(1) },
                { label: "Tenengrad", value: result.tenengrad_score.toFixed(2) },
              ].map(({ label, value }) => (
                <div key={label} style={{ background: "#fff", borderRadius: 8, padding: "10px 12px", border: "1px solid #e5e7eb", textAlign: "center" }}>
                  <p style={{ margin: 0, fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
                  <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 20, color: "#111827" }}>{value}</p>
                </div>
              ))}
            </div>

            <ScoreBar score={result.composite_score} />

            <div style={{ marginTop: 12, display: "inline-block", padding: "4px 14px", borderRadius: 20, fontSize: 13, fontWeight: 700, background: gradeStyle.bg, color: gradeStyle.text, border: `1px solid ${gradeStyle.border}` }}>
              Grade: {result.grade}
            </div>

            <p style={{ margin: "14px 0 0", fontSize: 14, color: accepted ? "#065f46" : "#7f1d1d" }}>
              {result.message}
            </p>

            <ProcessLog steps={result.process_log} />

            {!accepted && (
              <div style={{ marginTop: 14, background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: "12px 16px" }}>
                <p style={{ margin: "0 0 8px", fontWeight: 700, fontSize: 13, color: "#92400e" }}>Tips for a clearer image:</p>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "#78350f" }}>
                  <li>Ensure the area is well-lit and avoid shadows on the document</li>
                  <li>Hold the device steady or rest it on a flat surface</li>
                  <li>Ensure the document is fully in focus before capturing</li>
                  <li>Keep the camera parallel to the document surface</li>
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AdminPage() {
  const [records, setRecords]     = useState([]);
  const [stats, setStats]         = useState(null);
  const [threshold, setThreshold] = useState("");
  const [newThreshold, setNewThreshold] = useState("");
  const [saving, setSaving]       = useState(false);
  const [saveMsg, setSaveMsg]     = useState("");

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    const [rec, cfg, st] = await Promise.all([
      axios.get(`${API}/api/records`),
      axios.get(`${API}/api/config/threshold`),
      axios.get(`${API}/api/stats`),
    ]);
    setRecords(rec.data);
    setThreshold(cfg.data.threshold);
    setNewThreshold(cfg.data.threshold);
    setStats(st.data);
  };

  const saveThreshold = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/api/config/threshold`, { threshold: parseFloat(newThreshold) });
      setThreshold(newThreshold);
      setSaveMsg("Threshold updated successfully.");
      setTimeout(() => setSaveMsg(""), 3000);
    } catch {
      setSaveMsg("Failed to update threshold.");
    } finally {
      setSaving(false);
    }
  };

  const decisionBadge = (d) => ({
    display: "inline-block", padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 700,
    background: d === "accepted" ? "#d1fae5" : "#fee2e2",
    color: d === "accepted" ? "#065f46" : "#7f1d1d",
  });

  const gradeBadge = (g) => {
    const s = GRADE_COLORS[g] || {};
    return { display: "inline-block", padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 700, background: s.bg, color: s.text };
  };

  return (
    <div>
      {/* Stats row */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
          {[
            { label: "Total Uploads",   value: stats.total,      color: "#1d4ed8" },
            { label: "Accepted",        value: stats.accepted,   color: "#16a34a" },
            { label: "Rejected",        value: stats.rejected,   color: "#dc2626" },
            { label: "Avg Blur Score",  value: `${stats.avg_score}/100`, color: "#7c3aed" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background: "#fff", borderRadius: 10, padding: "16px 20px", boxShadow: "0 1px 6px rgba(0,0,0,0.07)", borderLeft: `4px solid ${color}` }}>
              <p style={{ margin: 0, fontSize: 12, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
              <p style={{ margin: "6px 0 0", fontWeight: 800, fontSize: 24, color: "#111827" }}>{value}</p>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>
        {/* Records table */}
        <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 6px rgba(0,0,0,0.07)", overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #f3f4f6" }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#111827" }}>Upload Records</h3>
            <p style={{ margin: "2px 0 0", fontSize: 13, color: "#9ca3af" }}>{records.length} total submissions</p>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  {["#", "Filename", "Format", "Score", "Grade", "Decision", "Timestamp"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "#6b7280", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "1px solid #f3f4f6" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: 32, textAlign: "center", color: "#9ca3af" }}>No uploads yet.</td></tr>
                )}
                {records.map((r, i) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #f9fafb", background: i % 2 === 0 ? "#fff" : "#fafafa" }}>
                    <td style={{ padding: "10px 14px", color: "#9ca3af" }}>{r.id}</td>
                    <td style={{ padding: "10px 14px", color: "#111827", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.file_name}</td>
                    <td style={{ padding: "10px 14px", color: "#6b7280" }}>{r.file_format}</td>
                    <td style={{ padding: "10px 14px", fontWeight: 700, color: "#111827" }}>{r.composite_score}</td>
                    <td style={{ padding: "10px 14px" }}><span style={gradeBadge(r.grade)}>{r.grade}</span></td>
                    <td style={{ padding: "10px 14px" }}><span style={decisionBadge(r.decision)}>{r.decision}</span></td>
                    <td style={{ padding: "10px 14px", color: "#9ca3af", whiteSpace: "nowrap" }}>
                      {r.timestamp ? new Date(r.timestamp).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Config panel */}
        <div>
          <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 6px rgba(0,0,0,0.07)", padding: 20, marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 700, color: "#111827" }}>Threshold Configuration</h3>
            <p style={{ margin: "0 0 16px", fontSize: 13, color: "#9ca3af" }}>Images scoring below this value will be rejected.</p>
            <p style={{ margin: "0 0 10px", fontSize: 13, color: "#6b7280" }}>Current threshold: <strong style={{ color: "#1d4ed8" }}>{threshold}/100</strong></p>
            <input type="number" min="0" max="100" value={newThreshold}
              onChange={(e) => setNewThreshold(e.target.value)}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid #d1d5db", fontSize: 14, boxSizing: "border-box", marginBottom: 10 }} />
            <button onClick={saveThreshold} disabled={saving}
              style={{ width: "100%", padding: "10px 0", borderRadius: 8, border: "none", background: saving ? "#d1d5db" : "#1d4ed8", color: "#fff", fontWeight: 700, fontSize: 14, cursor: saving ? "not-allowed" : "pointer" }}>
              {saving ? "Saving..." : "Update Threshold"}
            </button>
            {saveMsg && <p style={{ margin: "10px 0 0", fontSize: 13, color: saveMsg.includes("success") ? "#16a34a" : "#dc2626" }}>{saveMsg}</p>}
          </div>

          {/* Grade distribution */}
          {stats && (
            <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 6px rgba(0,0,0,0.07)", padding: 20 }}>
              <h3 style={{ margin: "0 0 14px", fontSize: 15, fontWeight: 700, color: "#111827" }}>Grade Distribution</h3>
              {Object.entries(stats.grade_distribution).map(([grade, count]) => {
                const s = GRADE_COLORS[grade] || {};
                const pct = stats.total > 0 ? Math.round((count / stats.total) * 100) : 0;
                return (
                  <div key={grade} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 3 }}>
                      <span style={{ fontWeight: 600, color: s.text }}>{grade}</span>
                      <span style={{ color: "#9ca3af" }}>{count} ({pct}%)</span>
                    </div>
                    <div style={{ background: "#f3f4f6", borderRadius: 6, height: 8 }}>
                      <div style={{ width: `${pct}%`, background: s.border, height: "100%", borderRadius: 6 }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("upload");

  const tabStyle = (t) => ({
    padding: "10px 28px", border: "none", cursor: "pointer", fontWeight: 700, fontSize: 14,
    background: tab === t ? "#fff" : "transparent",
    color: tab === t ? "#1d4ed8" : "#6b7280",
    borderBottom: tab === t ? "2px solid #1d4ed8" : "2px solid transparent",
    transition: "all 0.15s",
  });

  return (
    <div style={{ minHeight: "100vh", background: "#f1f5f9", fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      {/* Header */}
      <div style={{ background: "#1e3a5f", padding: "0 32px", display: "flex", alignItems: "center", gap: 16, boxShadow: "0 2px 8px rgba(0,0,0,0.2)" }}>
        <div style={{ padding: "16px 0" }}>
          <p style={{ margin: 0, fontWeight: 800, fontSize: 17, color: "#fff", letterSpacing: "0.01em" }}>
            🔍 BlurDetect
          </p>
          <p style={{ margin: 0, fontSize: 11, color: "#93c5fd" }}>Automated Identity Document Image Quality System</p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex" }}>
          <button style={tabStyle("upload")} onClick={() => setTab("upload")}>Upload</button>
          <button style={tabStyle("admin")} onClick={() => setTab("admin")}>Admin Dashboard</button>
        </div>
      </div>

      {/* Page content */}
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ margin: "0 0 4px", fontSize: 22, fontWeight: 800, color: "#111827" }}>
            {tab === "upload" ? "Document Image Upload" : "Administrator Dashboard"}
          </h1>
          <p style={{ margin: 0, fontSize: 14, color: "#6b7280" }}>
            {tab === "upload"
              ? "Upload an identity document image to assess its quality before verification."
              : "Review all upload records, configure the blur threshold, and monitor system performance."}
          </p>
        </div>
        {tab === "upload" ? <UploadPage /> : <AdminPage />}
      </div>
    </div>
  );
}
