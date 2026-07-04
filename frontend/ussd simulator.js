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
