// USSD Simulator

let dialBuffer = "";
let sessionId = "sim_" + Math.random().toString(36).slice(2, 10);
let accumulatedInput = "";
let inSession = false;

const screen = document.getElementById("screenContent");
const inputDisplay = document.getElementById("inputDisplay");
const log = document.getElementById("log");


function logLine(kind, text) {
  const div = document.createElement("div");
  div.className = kind;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}


async function callUssd() {
  const body = new URLSearchParams();
  body.append("sessionId", sessionId);
  body.append("serviceCode", "*384*69699#");
  body.append("phoneNumber", "+250788000001");
  body.append("text", accumulatedInput);
  logLine("req", `POST /ussd  text="${accumulatedInput}"`);
  const res = await fetch("/ussd", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString()
  });
  const txt = await res.text();
  logLine("res", txt.slice(0, 200));
  return txt;
}


function renderScreen(text) {
  // text starts with "CON " or "END "
  const kind = text.slice(0, 3);
  const body = text.slice(4);
  screen.textContent = body;
  if (kind === "END") {
    inSession = false;
    setTimeout(() => {
      screen.textContent = "Call ended.\nPress *384*69699# to start again.";
      accumulatedInput = "";
      sessionId = "sim_" + Math.random().toString(36).slice(2, 10);
    }, 3500);
  }
}


async function onSend() {
  if (!inSession) {
    // starting: dialBuffer should equal *384*69699#
    if (dialBuffer.includes("*384*69699#") || dialBuffer === "*384*69699#") {
      inSession = true;
      dialBuffer = "";
      inputDisplay.textContent = "_";
      accumulatedInput = "";
      const res = await callUssd();
      renderScreen(res);
    } else {
      screen.textContent = "Dial *384*69699# to start.";
      dialBuffer = "";
      inputDisplay.textContent = "_";
    }
  } else {
    
    accumulatedInput = accumulatedInput
      ? accumulatedInput + "*" + dialBuffer
      : dialBuffer;
    dialBuffer = "";
    inputDisplay.textContent = "_";
    const res = await callUssd();
    renderScreen(res);
  }
}

document.querySelectorAll("[data-k]").forEach(b => {
  b.addEventListener("click", () => {
    dialBuffer += b.dataset.k;
    inputDisplay.textContent = dialBuffer || "_";
  });
});


document.getElementById("sendBtn").addEventListener("click", onSend);
document.getElementById("clearBtn").addEventListener("click", () => {
  dialBuffer = "";
  inputDisplay.textContent = "_";
});


async function quickDial(code, followups = []) {
  // Reset
  dialBuffer = code;
  inputDisplay.textContent = code;
  inSession = false;
  sessionId = "sim_" + Math.random().toString(36).slice(2, 10);
  accumulatedInput = "";
  await onSend();
  for (const f of followups) {
    await new Promise(r => setTimeout(r, 900));
    dialBuffer = f;
    inputDisplay.textContent = f;
    await onSend();
  }
}