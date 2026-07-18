
let password = "";
let currentEscalationId = null;

function reasonPill(reason) {
  const urgent = ["suicidal_ideation", "medical_emergency", "gbv", "child_safeguarding"];
  const cls = urgent.includes(reason) ? "urgent" : "info";
  return `<span class="pill ${cls}">${reason}</span>`;
}

async function apiGet(path) {
  const res = await fetch(path, { headers: { "X-Dashboard-Password": password } });
  if (res.status === 401) { alert("Wrong password"); throw new Error("auth"); }
  return res.json();
}

async function loadDashboard() {
  try {
    const [stats, escalations] = await Promise.all([
      apiGet("/counselor/stats"),
      apiGet("/counselor/escalations?status=pending"),
    ]);
    renderStats(stats);
    renderEscalations(escalations);
    document.getElementById("tsNow").textContent = new Date().toLocaleString();
  } catch (e) {
    console.error(e);
  }
}


function renderStats(s) {
  const el = document.getElementById("stats");
  el.innerHTML = `
    <div class="stat-card urgent">
      <div class="label">Pending escalations</div>
      <div class="value">${s.escalations_pending}</div>
    </div>
    <div class="stat-card">
      <div class="label">Total sessions</div>
      <div class="value">${s.sessions_total}</div>
    </div>
    <div class="stat-card">
      <div class="label">Total escalations</div>
      <div class="value">${s.escalations_total}</div>
    </div>
    <div class="stat-card">
      <div class="label">By channel</div>
      <div class="value" style="font-size:1rem;font-family:inherit">
        ${Object.entries(s.sessions_by_channel).map(([k,v]) => `${k}: ${v}`).join(" · ") || "—"}
      </div>
    </div>
  `;
}

function formatAge(mins) {
  if (mins < 60) return `${mins}m ago`;
  if (mins < 60 * 24) return `${Math.floor(mins/60)}h ${mins%60}m`;
  return `${Math.floor(mins/60/24)}d ${Math.floor(mins/60)%24}h`;
}

function slaBadge(mins, reason) {
  const urgent = ["suicidal_ideation", "medical_emergency", "gbv", "child_safeguarding"];
  const target = urgent.includes(reason) ? 60 : 24 * 60;
  const pct = mins / target;
  const color = pct > 1 ? "var(--urgent)" : pct > 0.5 ? "var(--clay)" : "var(--ok)";
  return `<span style="color:${color};font-weight:600">${formatAge(mins)}</span>`;
}


