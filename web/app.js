const VAULT_STORAGE_KEY = "nitpicker.vault.v1";

const gate = document.getElementById("vaultGate");
const gateStatus = document.getElementById("gateStatus");
const sealForm = document.getElementById("sealForm");
const unlockForm = document.getElementById("unlockForm");
const enterStudioBtn = document.getElementById("enterStudioBtn");
const forgetVaultBtn = document.getElementById("forgetVaultBtn");
const openGateBtn = document.getElementById("openGateBtn");

const scoreForm = document.getElementById("scoreForm");
const runScoreBtn = document.getElementById("runScoreBtn");
const resultCard = document.getElementById("resultCard");
const formStatus = document.getElementById("formStatus");
const soundToggleBtn = document.getElementById("soundToggleBtn");

const encoder = new TextEncoder();
const decoder = new TextDecoder();

let unlockedApiKey = "";
let soundEnabled = false;


function setStatus(el, text, level = "") {
  el.textContent = text;
  el.classList.remove("error", "success");
  if (level) {
    el.classList.add(level);
  }
}


function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}


function randomBytes(length) {
  const bytes = new Uint8Array(length);
  window.crypto.getRandomValues(bytes);
  return bytes;
}


function bytesToBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}


function base64ToBytes(text) {
  const binary = window.atob(text);
  const output = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    output[i] = binary.charCodeAt(i);
  }
  return output;
}


async function deriveVaultKey(passphrase, salt) {
  const keyMaterial = await window.crypto.subtle.importKey(
    "raw",
    encoder.encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"],
  );

  return window.crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt,
      iterations: 250000,
      hash: "SHA-256",
    },
    keyMaterial,
    {
      name: "AES-GCM",
      length: 256,
    },
    false,
    ["encrypt", "decrypt"],
  );
}


async function encryptSecret(secret, passphrase) {
  const salt = randomBytes(16);
  const iv = randomBytes(12);
  const key = await deriveVaultKey(passphrase, salt);

  const cipherBuffer = await window.crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoder.encode(secret),
  );

  return {
    version: 1,
    salt: bytesToBase64(salt),
    iv: bytesToBase64(iv),
    ciphertext: bytesToBase64(new Uint8Array(cipherBuffer)),
  };
}


async function decryptSecret(vault, passphrase) {
  const salt = base64ToBytes(vault.salt);
  const iv = base64ToBytes(vault.iv);
  const ciphertext = base64ToBytes(vault.ciphertext);
  const key = await deriveVaultKey(passphrase, salt);

  const plainBuffer = await window.crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    key,
    ciphertext,
  );

  return decoder.decode(plainBuffer);
}


function getStoredVault() {
  const raw = window.localStorage.getItem(VAULT_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}


function openGate() {
  gate.classList.add("open");
  document.body.classList.add("locked");
}


function closeGate() {
  if (!unlockedApiKey) {
    return;
  }
  gate.classList.remove("open");
  document.body.classList.remove("locked");
}


function updateGateHint() {
  if (getStoredVault()) {
    setStatus(gateStatus, "Existing vault detected. Enter your passphrase to continue.");
  } else {
    setStatus(gateStatus, "No local vault found. Seal your key and passphrase to begin.");
  }
}


function playPing(type = "soft") {
  if (!soundEnabled) {
    return;
  }

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return;
  }

  if (!window.__nitpickerAudioCtx) {
    window.__nitpickerAudioCtx = new AudioContextClass();
  }

  const ctx = window.__nitpickerAudioCtx;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  const now = ctx.currentTime;
  osc.type = type === "warn" ? "square" : "triangle";
  osc.frequency.value = type === "warn" ? 220 : 520;

  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.03, now + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.11);

  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.12);
}


function setRunState(running) {
  runScoreBtn.disabled = running;
  runScoreBtn.textContent = running ? "Analyzing..." : "Run Analysis";
}


function renderResult(data) {
  const scores = data.scores || {};
  const metricRows = ["accuracy", "completeness", "clarity", "overall"]
    .map((key) => {
      const value = Number(scores[key] || 0);
      const width = Math.max(0, Math.min(100, value * 10));
      return `
        <div class="score-item">
          <div class="score-label"><span>${escapeHtml(key)}</span><strong>${value.toFixed(1)}</strong></div>
          <div class="meter"><div class="meter-fill" style="width:${width}%"></div></div>
        </div>
      `;
    })
    .join("");

  const confidence = Number(data.confidence || 0);
  const confidenceLevel = confidence >= 0.75 ? "high" : confidence >= 0.5 ? "medium" : "low";

  const strengths = Array.isArray(data.strengths)
    ? data.strengths.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "";

  const issues = Array.isArray(data.issues)
    ? data.issues
        .map((item) => {
          const issueType = escapeHtml(item.issue_type || "issue");
          const severity = escapeHtml(item.severity || "medium");
          const detail = escapeHtml(item.detail || "");
          return `<li><strong>[${severity}] ${issueType}</strong> ${detail}</li>`;
        })
        .join("")
    : "";

  const notes = Array.isArray(data.notes)
    ? data.notes.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "";

  const rewrite = escapeHtml(data.rewrite_suggestion || "");

  resultCard.classList.remove("empty");
  resultCard.innerHTML = `
    <div class="score-grid">${metricRows}</div>
    <div class="result-section">
      <h3>Confidence</h3>
      <span class="pill ${confidenceLevel}">${confidence.toFixed(2)}</span>
    </div>
    <div class="result-section">
      <h3>Strengths</h3>
      <ul>${strengths || "<li>No strengths returned.</li>"}</ul>
    </div>
    <div class="result-section">
      <h3>Issues</h3>
      <ul>${issues || "<li>No issues returned.</li>"}</ul>
    </div>
    <div class="result-section">
      <h3>Rewrite Suggestion</h3>
      <p>${rewrite || "No rewrite suggestion returned."}</p>
    </div>
    <div class="result-section">
      <h3>Notes</h3>
      <ul>${notes || "<li>No notes returned.</li>"}</ul>
    </div>
  `;
}


sealForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  playPing();

  const apiKey = document.getElementById("apiKeyInput").value.trim();
  const passphrase = document.getElementById("sealPassInput").value;

  if (apiKey.length < 8) {
    setStatus(gateStatus, "API key looks too short.", "error");
    playPing("warn");
    return;
  }
  if (passphrase.length < 8) {
    setStatus(gateStatus, "Passphrase must be at least 8 characters.", "error");
    playPing("warn");
    return;
  }

  try {
    const vault = await encryptSecret(apiKey, passphrase);
    window.localStorage.setItem(VAULT_STORAGE_KEY, JSON.stringify(vault));
    unlockedApiKey = apiKey;
    enterStudioBtn.disabled = false;
    setStatus(gateStatus, "Vault sealed and unlocked for this session.", "success");
    document.getElementById("apiKeyInput").value = "";
    document.getElementById("sealPassInput").value = "";
  } catch {
    setStatus(gateStatus, "Failed to seal the vault in this browser.", "error");
  }
});


unlockForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  playPing();

  const vault = getStoredVault();
  if (!vault) {
    setStatus(gateStatus, "No stored vault found. Seal a key first.", "error");
    return;
  }

  const passphrase = document.getElementById("unlockPassInput").value;
  if (!passphrase) {
    setStatus(gateStatus, "Enter passphrase to unlock.", "error");
    return;
  }

  try {
    const apiKey = await decryptSecret(vault, passphrase);
    unlockedApiKey = apiKey;
    enterStudioBtn.disabled = false;
    setStatus(gateStatus, "Vault unlocked. Welcome back.", "success");
    document.getElementById("unlockPassInput").value = "";
  } catch {
    setStatus(gateStatus, "Unlock failed. Wrong passphrase or damaged vault.", "error");
    playPing("warn");
  }
});


forgetVaultBtn.addEventListener("click", () => {
  playPing("warn");
  window.localStorage.removeItem(VAULT_STORAGE_KEY);
  unlockedApiKey = "";
  enterStudioBtn.disabled = true;
  setStatus(gateStatus, "Stored vault removed from this browser.", "success");
  updateGateHint();
});


enterStudioBtn.addEventListener("click", () => {
  playPing();
  closeGate();
  setStatus(formStatus, "Vault unlocked. Ready to analyze comments.", "success");
});


openGateBtn.addEventListener("click", () => {
  openGate();
  updateGateHint();
});


scoreForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  playPing();

  if (!unlockedApiKey) {
    openGate();
    setStatus(gateStatus, "Unlock your vault first.", "error");
    return;
  }

  const language = document.getElementById("languageInput").value.trim() || "unknown";
  const functionCode = document.getElementById("functionCodeInput").value;
  const commentText = document.getElementById("commentTextInput").value;
  const context = document.getElementById("contextInput").value;
  const model = document.getElementById("modelInput").value.trim();
  const baseUrl = document.getElementById("baseUrlInput").value.trim();
  const fast = document.getElementById("fastModeInput").checked;

  if (!functionCode.trim() || !commentText.trim()) {
    setStatus(formStatus, "Function code and comment are required.", "error");
    playPing("warn");
    return;
  }

  const payload = {
    api_key: unlockedApiKey,
    language,
    function_code: functionCode,
    comment_text: commentText,
    context,
    model: model || null,
    base_url: baseUrl || null,
    fast,
  };

  setRunState(true);
  setStatus(formStatus, "Analyzer is reviewing your code...", "");

  try {
    const response = await window.fetch("/api/score", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "Scoring request failed.";
      throw new Error(detail);
    }

    renderResult(data);
    setStatus(formStatus, "Analysis complete.", "success");
    document.getElementById("result").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Scoring failed unexpectedly.";
    setStatus(formStatus, message, "error");
    playPing("warn");
  } finally {
    setRunState(false);
  }
});


soundToggleBtn.addEventListener("click", () => {
  soundEnabled = !soundEnabled;
  soundToggleBtn.textContent = soundEnabled ? "SOUND ON" : "SOUND OFF";
  soundToggleBtn.setAttribute("aria-pressed", soundEnabled ? "true" : "false");
  playPing();
});


document.querySelectorAll(".lift-btn").forEach((btn) => {
  btn.addEventListener("pointerdown", () => playPing());
});


updateGateHint();
openGate();

if (getStoredVault()) {
  setStatus(gateStatus, "Vault detected. Unlock to continue.");
} else {
  setStatus(gateStatus, "Seal your API key to start.");
}
