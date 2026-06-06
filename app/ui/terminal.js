const providerSelect = document.getElementById("provider-select");
const modelInput = document.getElementById("model-input");
const apiKeyInput = document.getElementById("api-key-input");
const sendButton = document.getElementById("send-button");
const userInput = document.getElementById("user-input");
const terminalWindow = document.getElementById("terminal-window");
const statusText = document.getElementById("status-text");
const serverStatus = document.getElementById("server-status");
const executionIdEl = document.getElementById("execution-id");
const nodesInfo = document.getElementById("nodes-info");
const durationInfo = document.getElementById("duration-info");
const refreshConfig = document.getElementById("refresh-config");
const saveConfigButton = document.getElementById("save-config");
const toggleSettings = document.getElementById("toggle-settings");
const configHelp = document.getElementById("config-help");
const apiKeyHint = document.getElementById("api-key-hint");

let lastAssistantLine = null;
let providerOptions = {};
let sessionConfig = {
  provider: "nvidia",
  api_key: "",
  model: ""
};

function scrollToBottom() {
  terminalWindow.scrollTop = terminalWindow.scrollHeight;
}

function appendLine(text, type = "assistant") {
  const line = document.createElement("div");
  line.className = `terminal-line ${type}`;
  line.textContent = text;
  terminalWindow.appendChild(line);
  scrollToBottom();
  return line;
}

function setStatus(value, isError = false) {
  statusText.textContent = value;
  serverStatus.textContent = value;
  serverStatus.style.background = isError ? "rgba(255, 115, 115, 0.16)" : "rgba(67, 171, 255, 0.16)";
}

function updateMetrics(metrics) {
  if (!metrics) return;
  executionIdEl.textContent = metrics.execution_id || executionIdEl.textContent || "—";
  nodesInfo.textContent = metrics.total_nodes ? `${metrics.completed_nodes || 0} / ${metrics.total_nodes}` : nodesInfo.textContent;
  durationInfo.textContent = metrics.total_duration_ms ? `${Math.round(metrics.total_duration_ms)} ms` : durationInfo.textContent;
}

function getProviderHint(provider) {
  const hints = {
    openai: "Starts with sk-...",
    anthropic: "Starts with sk-...",
    nvidia: "Starts with nvapi-...",
    gemini: "Starts with a Gemini key or OAuth token",
    huggingface: "Starts with hf_...",
    grok: "Starts with xai_..."
  };
  return hints[provider] || "Enter the API key for the selected provider.";
}

function updateProviderHint(provider) {
  const hint = getProviderHint(provider);
  apiKeyHint.textContent = hint;
  apiKeyInput.placeholder = hint;
}

function loadSavedConfig() {
  try {
    const saved = JSON.parse(localStorage.getItem("dragon_terminal_config") || "{}");
    if (!saved) return;

    if (saved.provider) {
      providerSelect.value = saved.provider;
    }
    if (saved.model) {
      modelInput.value = saved.model;
    }
    if (saved.api_key) {
      apiKeyInput.value = saved.api_key;
    }

    updateProviderHint(providerSelect.value);
    setStatus("Configuration loaded from browser storage");
  } catch (error) {
    console.warn("Unable to load saved config", error);
  }
}

function saveLocalConfig() {
  const config = {
    provider: providerSelect.value,
    model: modelInput.value.trim(),
    api_key: apiKeyInput.value.trim()
  };
  localStorage.setItem("dragon_terminal_config", JSON.stringify(config));
  setStatus("Config saved locally");
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) {
      throw new Error(`Failed to load configuration: ${response.status}`);
    }
    const data = await response.json();
    const providers = data.providers || {};
    providerOptions = providers;

    providerSelect.innerHTML = Object.keys(providers)
      .map(key => `<option value="${key}">${key}</option>`)
      .join("");

    const defaultProvider = Object.entries(providers).find(([, value]) => value.default) || Object.entries(providers)[0];
    if (defaultProvider) {
      sessionConfig.provider = defaultProvider[0];
      providerSelect.value = sessionConfig.provider;
      modelInput.value = defaultProvider[1].default_model || "";
    }

    loadSavedConfig();
    updateProviderHint(providerSelect.value);
    serverStatus.textContent = "Ready";
    setStatus("Ready");
  } catch (error) {
    setStatus("Config load failed", true);
    appendLine(`⚠️ ${error.message}`, "error");
  }
}

function buildPayload(message) {
  const config = {
    provider: providerSelect.value,
    api_key: apiKeyInput.value.trim(),
    model: modelInput.value.trim() || undefined
  };

  return {
    message,
    config
  };
}

function createStreamParser(onUpdate, onComplete, onError) {
  let buffer = "";

  return chunk => {
    buffer += chunk;
    const parts = buffer.split(/\n\n/);
    buffer = parts.pop();

    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed) continue;

      const line = trimmed.split(/\n/)
        .filter(item => item.startsWith("data:"))
        .map(item => item.slice(5).trim())
        .join("");

      if (!line) continue;
      if (line === "[DONE]") {
        onComplete();
        continue;
      }

      try {
        const payload = JSON.parse(line);
        if (payload.error) {
          onError(payload.error);
          continue;
        }

        if (payload.content !== undefined) {
          onUpdate(payload.content, payload.metrics);
        }

        if (payload.metrics) {
          onComplete(payload.metrics);
        }
      } catch (err) {
        onError(err.message);
      }
    }
  };
}

async function streamChat(message) {
  const assistantLine = appendLine("", "assistant");
  lastAssistantLine = assistantLine;
  setStatus("Streaming response...");
  statusText.textContent = "Running";

  try {
    const response = await fetch("/api/chat-stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(buildPayload(message))
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Server returned ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parser = createStreamParser(
      (content, metrics) => {
        assistantLine.textContent = content;
        if (metrics) {
          updateMetrics(metrics);
        }
      },
      metrics => {
        setStatus("Completed");
        if (metrics) updateMetrics(metrics);
      },
      error => {
        assistantLine.textContent = `Error: ${error}`;
        assistantLine.classList.add("error");
        setStatus("Error", true);
      }
    );

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      parser(decoder.decode(value, { stream: true }));
    }

    parser("\n\n");
  } catch (error) {
    setStatus("Error", true);
    appendLine(`⚠️ ${error.message}`, "error");
  }
}

async function sendMessage() {
  const message = userInput.value.trim();
  if (!message) return;

  appendLine(`> ${message}`, "user");
  userInput.value = "";
  updateMetrics({});
  await streamChat(message);
}

refreshConfig.addEventListener("click", () => {
  loadConfig();
});

providerSelect.addEventListener("change", () => {
  const provider = providerSelect.value;
  const current = providerOptions[provider];
  if (current && current.default_model) {
    modelInput.value = current.default_model;
  }
  updateProviderHint(provider);
});

saveConfigButton.addEventListener("click", () => {
  saveLocalConfig();
});

toggleSettings.addEventListener("click", () => {
  const visible = configHelp.style.display !== "block";
  configHelp.style.display = visible ? "block" : "none";
});

sendButton.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

window.addEventListener("load", async () => {
  await loadConfig();
  appendLine("Welcome to the Dragon Terminal UI. Enter a request below.", "status");
});
