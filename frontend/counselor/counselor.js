
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