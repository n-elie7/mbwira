const params = new URLSearchParams(location.search);
const roomId = params.get("room");
const role = params.get("role") === "counselor" ? "counselor" : "user";
const lang = params.get("lang") === "en" ? "en" : (role === "counselor" ? "en" : "rw");

const strings = {
    rw: {
        privacy: "Ikiganiro ni ibanga",
        waiting: "Tegereza gato...",
        waitingSub: "Umujyanama ari hafi kwinjira mu kiganiro. Komeza ufungure iyi paji.",
        connecting: "Turimo Kubahuza...",
        connectingSub: "Guhuza amashusho n'amajwi birimo gukorwa.",
        connected: "Muvugane n'umujyanama",
        peerLeft: "Uwo muvagana yavuye mu kiganiro.",
        peerLeftSub: "Ushobora gutegereza ko agaruka ugasoza ikiganiro.",
        ended: "Ikiganiro cyarangiye.",
        endedSub: "Urashobora gufunga iyi paji. Komeza wandikirane na Mbwira igihe ubishaka.",
        mediaError: "Ntibishoboka gufungura kamera cyangwa mikoro.",
        mediaErrorSub: "Emera uburenganzira bwa kamera na mikoro muri browser hanyuma wongere ugerageze.",
        invalid: "Iki kiganiro nticyabonetse cyangwa cyarangiye."
    },
    en: {
        privacy: "This call is private",
        waiting: "Waiting for the other side...",
        waitingSub: role === "counselor"
            ? "The user is being connected. Keep this page open."
            : "A counselor will join shortly. Keep this page open.",
        connecting: "Connecting...",
        connectingSub: "Setting up secure audio and video.",
        connected: role === "counselor" ? "Connected with the user" : "Connected with a counselor",
        peerLeft: "The other participant left the call.",
        peerLeftSub: "You can wait for them to rejoin, or end the call.",
        ended: "The call has ended.",
        endedSub: "You can close this page now.",
        mediaError: "Could not access camera or microphone.",
        mediaErrorSub: "Allow camera and microphone permissions in your browser, then reload this page.",
        invalid: "This call was not found or has already ended."
    }
};
const t = strings[lang];
document.getElementById("privacyPill").textContent = t.privacy;

const overlay = document.getElementById("statusOverlay");
const statusTitle = document.getElementById("statusTitle");
const statusSub = document.getElementById("statusSub");

function setStatus(title, sub = "", show = true) {
  statusTitle.textContent = title;
  statusSub.textContent = sub;
  overlay.classList.toggle("hidden", !show);
}

let ws = null;
let pc = null;
let localStream = null;
let callOver = false;

const rtcConfig = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
};

function newPeerConnection() {
  if (pc) pc.close();
  pc = new RTCPeerConnection(rtcConfig);
  localStream.getTracks().forEach(tr => pc.addTrack(tr, localStream));
  pc.ontrack = (e) => {
    document.getElementById("remoteVideo").srcObject = e.streams[0];
    setStatus("", "", false);
  };
  pc.onicecandidate = (e) => {
    if (e.candidate) send({ type: "ice", candidate: e.candidate });
  };
  pc.onconnectionstatechange = () => {
    if (pc.connectionState === "connected") setStatus("", "", false);
    if (pc.connectionState === "failed") setStatus(t.connecting, t.connectingSub);
  };
  return pc;
}

function send(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
}


async function makeOffer() {
  newPeerConnection();
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  send({ type: "offer", sdp: pc.localDescription });
}

async function handleSignal(msg) {
  if (msg.type === "room-state") {
    if (msg.peers.length === 0) {
      setStatus(t.waiting, t.waitingSub);
    } else {
      setStatus(t.connecting, t.connectingSub);
      if (role === "counselor") await makeOffer();
    }
  } else if (msg.type === "peer-joined") {
    setStatus(t.connecting, t.connectingSub);
    if (role === "counselor") await makeOffer();
  } else if (msg.type === "offer") {
    newPeerConnection();
    await pc.setRemoteDescription(msg.sdp);
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    send({ type: "answer", sdp: pc.localDescription });
  } else if (msg.type === "answer") {
    if (pc) await pc.setRemoteDescription(msg.sdp);
  } else if (msg.type === "ice") {
    if (pc) {
      try { await pc.addIceCandidate(msg.candidate); } catch (e) { console.warn(e); }
    }
  } else if (msg.type === "peer-left") {
    document.getElementById("remoteVideo").srcObject = null;
    setStatus(t.peerLeft, t.peerLeftSub);
  } else if (msg.type === "bye") {
    endLocally();
  }
}

function connectWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/calls/ws/${roomId}?role=${role}`);
  ws.onmessage = (e) => handleSignal(JSON.parse(e.data)).catch(console.error);
  ws.onclose = (e) => {
    if (callOver) return;
    if (e.code === 4404) {
      setStatus(t.invalid, "");
    } else if (e.code === 4409) {
      setStatus(t.invalid, "");
    } else {
      // transient drop - try to come back
      setTimeout(() => { if (!callOver) connectWs(); }, 2000);
    }
  };
}

function endLocally() {
  callOver = true;
  if (pc) pc.close();
  if (ws) ws.close();
  if (localStream) localStream.getTracks().forEach(tr => tr.stop());
  document.getElementById("remoteVideo").srcObject = null;
  document.getElementById("localVideo").srcObject = null;
  setStatus(t.ended, t.endedSub);
}

document.getElementById("endBtn").onclick = async () => {
  send({ type: "bye" });
  try {
    await fetch(`/calls/${roomId}/end`, { method: "POST" });
  } catch (e) { /* best effort */ }
  endLocally();
};

document.getElementById("micBtn").onclick = (e) => {
  if (!localStream) return;
  const track = localStream.getAudioTracks()[0];
  if (!track) return;
  track.enabled = !track.enabled;
  e.currentTarget.classList.toggle("off", !track.enabled);
};

document.getElementById("camBtn").onclick = (e) => {
  if (!localStream) return;
  const track = localStream.getVideoTracks()[0];
  if (!track) return;
  track.enabled = !track.enabled;
  e.currentTarget.classList.toggle("off", !track.enabled);
};


window.addEventListener("pagehide", () => {
  if (role === "user" && !callOver) {
    navigator.sendBeacon(`/calls/${roomId}/end`);
  }
});

async function init() {
  if (!roomId) { setStatus(t.invalid, ""); return; }
  setStatus(t.connecting, t.connectingSub);
  try {
    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  } catch (err) {
    console.error(err);
    setStatus(t.mediaError, t.mediaErrorSub);
    return;
  }
  document.getElementById("localVideo").srcObject = localStream;
  setStatus(t.waiting, t.waitingSub);
  connectWs();
}

init();
