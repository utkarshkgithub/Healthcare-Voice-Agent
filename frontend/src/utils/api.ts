/**
 * API client — talks to the real FastAPI backend.
 * Endpoint paths match backend/main.py router registrations exactly.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ─── Generic fetch wrapper ─────────────────────────────────────────────────────
async function apiFetch<T>(
  method: 'GET' | 'POST',
  path: string,
  body?: unknown,
): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }

  return res.json();
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  /**
   * POST /auth/login
   * Returns { message, user_id, name, email }
   */
  login: (email: string, password: string) =>
    apiFetch<{ message: string; user_id: string; name?: string; email?: string }>('POST', '/auth/login', { email, password }),

  /**
   * POST /auth/register
   * Returns { message, user_id, name, email }
   */
  register: (name: string, email: string, password: string) =>
    apiFetch<{ message: string; user_id: string; name?: string; email?: string }>('POST', '/auth/register', { name, email, password }),

  /**
   * GET /auth/me/{userId}
   * Returns { email, name }
   */
  getMe: (userId: string) =>
    apiFetch<{ email: string; name: string }>('GET', `/auth/me/${userId}`),

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_email');
    localStorage.removeItem('voice_sessions');
  },
};


// ─── Chat (LangGraph voice agent) ─────────────────────────────────────────────
export const chatApi = {
  /**
   * POST /chat
   * Sends a message + conversation history to the LangGraph pipeline.
   * Returns { reply: string }
   */
  send: (message: string, history: string[] = []) =>
    apiFetch<{ reply: string }>('POST', '/chat', { message, history }),
};

// ─── Voice (STT / TTS via backend voice provider) ─────────────────────────────
export const voiceApi = {
  /**
   * POST /stt
   * Uploads an audio Blob to the backend for server-side speech-to-text.
   * Only functional when VOICE_PROVIDER=deepgram on the backend.
   * Returns { text: string }
   */
  stt: async (audioBlob: Blob): Promise<{ text: string }> => {
    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const res = await fetch(`${API_BASE}/stt`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`${res.status}: ${text}`);
    }
    return res.json();
  },

  /**
   * POST /tts
   * Sends text to the backend for server-side text-to-speech.
   * Only functional when VOICE_PROVIDER=deepgram on the backend.
   * Returns raw audio ArrayBuffer (MP3).
   */
  tts: async (text: string): Promise<ArrayBuffer> => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_BASE}/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => res.statusText);
      throw new Error(`${res.status}: ${errText}`);
    }
    return res.arrayBuffer();
  },
};
