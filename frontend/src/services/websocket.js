export function createRecognitionSocket(config, onMessage, onClose) {
  const wsBase = (import.meta.env.VITE_WS_URL || "ws://localhost:8000").replace(/\/$/, "");
  const ws = new WebSocket(`${wsBase}/ws/process`);

  ws.onopen = () => {
    ws.send(JSON.stringify(config));
  };

  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      onMessage(payload);
    } catch (err) {
      onMessage({ type: "error", message: "Invalid WebSocket payload" });
    }
  };

  ws.onerror = () => {
    onMessage({
      type: "error",
      message: "WebSocket connection failed. Check backend availability and login session.",
    });
  };

  ws.onclose = (event) => {
    if (event.code === 1008) {
      onMessage({ type: "error", message: "WebSocket authorization failed. Please sign in again." });
    }
    if (onClose) onClose(event);
  };

  return ws;
}
