
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

function renderEscalations(list) {
  const el = document.getElementById("escalationList");
  if (!list.length) {
    el.innerHTML = `<div class="empty">No pending escalations. Good news.</div>`;
    return;
  }
  el.innerHTML = `
    <div class="escalation-table">
      <div class="escalation-row header">
        <div>Age</div>
        <div>Reason</div>
        <div>Channel</div>
        <div>Notes</div>
        <div>Reachable?</div>
      </div>
      ${list.map(e => `
        <div class="escalation-row" data-id="${e.id}">
          <div>${slaBadge(e.age_minutes, e.reason)}</div>
          <div>${reasonPill(e.reason)}</div>
          <div><span class="channel-pill">${e.channel}</span></div>
          <div style="font-size:0.85rem;color:var(--muted)">
            ${(e.notes || "").slice(0, 100)}${(e.notes||"").length>100?"…":""}
          </div>
          <div>${e.contact_available ? "📞 yes" : "—"}</div>
        </div>
      `).join("")}
    </div>
  `;
  el.querySelectorAll(".escalation-row[data-id]").forEach(row => {
    row.onclick = () => openModal(parseInt(row.dataset.id));
  });
}

let currentEscalationData = null;

async function openModal(id) {
  currentEscalationId = id;
  const messages = await apiGet(`/counselor/escalations/${id}/messages`);
  const body = document.getElementById("modalBody");
  body.innerHTML = messages.map(m => `
    <div class="msg-bubble ${m.role} ${m.flagged ? "flagged" : ""}">
      ${m.content.replace(/</g, "&lt;")}
      <div class="msg-meta">${m.role} · ${new Date(m.created_at).toLocaleString()}
      ${m.flag_reason ? "· ⚠ " + m.flag_reason : ""}</div>
    </div>
  `).join("");

 
  const list = await apiGet("/counselor/escalations?status=pending");
  const fromPending = list.find(e => e.id === id);
  if (!fromPending) {
    const takenList = await apiGet("/counselor/escalations?status=taken");
    currentEscalationData = takenList.find(e => e.id === id) || { channel: "?", contact_available: false };
  } else {
    currentEscalationData = fromPending;
  }


  document.getElementById("revealedNumber").style.display = "none";
  document.getElementById("outboundArea").style.display = "none";
  document.getElementById("outboundText").value = "";
  const info = document.getElementById("contactInfo");
  const sendBtn = document.getElementById("sendWhatsappBtn");
  const revealBtn = document.getElementById("revealBtn");

  if (!currentEscalationData.contact_available) {
    info.innerHTML = `<strong>⚠ No contact number on file.</strong> This user cannot be called back directly. Consider posting a reply through the channel they used, or waiting for them to return.`;
    revealBtn.disabled = true;
    sendBtn.disabled = true;
    revealBtn.style.opacity = "0.4";
    sendBtn.style.opacity = "0.4";
  } else {
    info.innerHTML = `Channel: <strong>${currentEscalationData.channel}</strong>. Reveal the number to call directly, or send a WhatsApp reply (WhatsApp sessions only).`;
    revealBtn.disabled = false;
    sendBtn.disabled = (currentEscalationData.channel !== "whatsapp");
    revealBtn.style.opacity = "1";
    sendBtn.style.opacity = (currentEscalationData.channel !== "whatsapp") ? "0.4" : "1";
  }

  document.getElementById("modalBackdrop").classList.add("visible");
}

document.getElementById("revealBtn").onclick = async () => {
  const reason = prompt("Why are you revealing this number? (logged in audit trail)",
    "Calling user regarding pending escalation");
  if (!reason) return;
  const res = await fetch(`/counselor/escalations/${currentEscalationId}/reveal-contact`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Dashboard-Password": password },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) { alert("Failed to reveal number."); return; }
  const data = await res.json();
  const el = document.getElementById("revealedNumber");
  el.style.display = "block";
  el.innerHTML = `📞 <a href="tel:${data.contact_number}" style="color:var(--cream);text-decoration:underline">${data.contact_number}</a>
    <span style="font-size:0.75rem;opacity:0.7;margin-left:0.5rem">(${data.channel})</span>`;
};

document.getElementById("sendWhatsappBtn").onclick = () => {
  document.getElementById("outboundArea").style.display = "block";
  document.getElementById("outboundText").focus();
};

document.getElementById("outboundSendBtn").onclick = async () => {
  const text = document.getElementById("outboundText").value.trim();
  if (!text) return;
  const res = await fetch(`/counselor/escalations/${currentEscalationId}/send-message`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Dashboard-Password": password },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert("Failed to send: " + (err.detail || res.statusText));
    return;
  }
  alert("Sent. The user will receive it on WhatsApp shortly.");
  document.getElementById("outboundText").value = "";
  document.getElementById("outboundArea").style.display = "none";
  await openModal(currentEscalationId);  // refresh transcript
};

document.getElementById("closeModal").onclick = () => {
  document.getElementById("modalBackdrop").classList.remove("visible");
};

document.getElementById("resolveBtn").onclick = async () => {
  const notes = document.getElementById("resolveNotes").value;
  await fetch(`/counselor/escalations/${currentEscalationId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Dashboard-Password": password },
    body: JSON.stringify({ notes }),
  });
  document.getElementById("modalBackdrop").classList.remove("visible");
  document.getElementById("resolveNotes").value = "";
  await loadDashboard();
};


document.getElementById("loginBtn").onclick = async () => {
  password = document.getElementById("pwd").value;
  try {
    await apiGet("/counselor/stats");
    document.getElementById("loginScreen").style.display = "none";
    document.getElementById("main").classList.add("visible");
    loadDashboard();
    setInterval(loadDashboard, 15000);
  } catch (e) { /* shown by apiGet */ }
};


document.getElementById("pwd").addEventListener("keypress", e => {
  if (e.key === "Enter") document.getElementById("loginBtn").click();
});
