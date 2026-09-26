import axios from "axios";

const BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

/**
 * Extract a readable, correctly-classified error from an Axios/HTTP error.
 * Distinguishes HTTP/API errors (with .status) from timeouts and pure
 * connection failures so the UI never shows "Cannot reach the server" for a
 * 422/404/500.
 */
function toApiError(error) {
  let message;
  let status;

  if (error.response) {
    status = error.response.status;
    const detail = error.response.data?.detail;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail) && detail.length > 0) {
      message = detail.map((d) => d.msg).join("; ");
    } else {
      message = `Server error (${status}). Please try again.`;
    }
  } else if (error.code === "ECONNABORTED") {
    message =
      "The request timed out. The server may still be loading — please try again.";
  } else if (error.request) {
    message = `Cannot reach the server at ${BASE_URL}. Make sure the backend is running.`;
  } else {
    message = error.message || "Something went wrong. Please try again.";
  }

  const apiError = new Error(message);
  if (status !== undefined) apiError.status = status;
  return apiError;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(toApiError(error)),
);

/** POST /api/chat — send a message, get TOM's local reply (persisted). */
export async function sendChatMessage(message, conversationId = null) {
  const payload = { message };
  if (conversationId) payload.conversation_id = conversationId;
  const { data } = await apiClient.post("/api/chat", payload);
  return data;
}

/** GET /api/conversations — persisted conversation summaries (newest first). */
export async function listConversations() {
  const { data } = await apiClient.get("/api/conversations");
  return data;
}

/** GET /api/conversations/{id}/messages — persisted messages. */
export async function getConversationMessages(conversationId) {
  const { data } = await apiClient.get(
    `/api/conversations/${conversationId}/messages`,
  );
  return data;
}

/** POST /api/screening/phq9/start — begin a PHQ-9 screening session. */
export async function startPhq9() {
  const { data } = await apiClient.post("/api/screening/phq9/start");
  return data;
}

/** GET /api/screening/phq9/{id} — current screening state. */
export async function getPhq9State(screeningId) {
  const { data } = await apiClient.get(`/api/screening/phq9/${screeningId}`);
  return data;
}

/** POST /api/screening/phq9/{id}/answer — submit one structured answer. */
export async function answerPhq9(screeningId, questionNumber, answer) {
  const { data } = await apiClient.post(
    `/api/screening/phq9/${screeningId}/answer`,
    { question_number: questionNumber, answer },
  );
  return data;
}

/** POST /api/screening/phq9/{id}/complete — score + severity (+ item-9 safety). */
export async function completePhq9(screeningId) {
  const { data } = await apiClient.post(
    `/api/screening/phq9/${screeningId}/complete`,
  );
  return data;
}
