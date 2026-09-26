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
export interface AuthResult {
  message: string;
  access_token: string;
  token_type: string;
  user_id: number;
  patient_id: number | null;
  name?: string;
  email?: string;
}

export const authApi = {
  /** POST /auth/login — returns a signed access token. */
  login: (email: string, password: string) =>
    apiFetch<AuthResult>('POST', '/auth/login', { email, password }),

  /** POST /auth/register — returns a signed access token. */
  register: (name: string, email: string, password: string) =>
    apiFetch<AuthResult>('POST', '/auth/register', { name, email, password }),

  /** GET /auth/me — identity resolved from the bearer token. */
  getMe: () =>
    apiFetch<{ email: string; name: string; user_id: number; patient_id: number | null }>('GET', '/auth/me'),

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('patient_id');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_email');
    localStorage.removeItem('voice_sessions');
  },
};


// ─── Chat (LangGraph voice agent) ─────────────────────────────────────────────
export interface ChatResult {
  reply: string;
  question_rounds: number;
  predicted_condition: string;
  predicted_additional_symptoms: string[];
  immediate_remedy: string;
  prediction_summary: string;
}

export const chatApi = {
  /**
   * POST /chat
   * Sends a message + conversation history to the LangGraph pipeline.
   *
   * question_rounds MUST be threaded back in on every call: the backend owns
   * the clarifying-question cap, and a client that keeps resetting it to 0
   * makes the agent question the patient indefinitely.
   */
  send: (message: string, history: string[] = [], questionRounds = 0) =>
    apiFetch<ChatResult>('POST', '/chat', {
      message,
      history,
      question_rounds: questionRounds,
    }),
};

// ─── Triage (specialist mapping + doctor discovery) ───────────────────────────
export interface Doctor {
  doctor_id: number;
  name: string;
  specialization: string;
  rating: number;
  fees: number;
  hospital: string;
  next_available_date: string;
  start_time: string;
  end_time: string;
  slot_id: number;
}

export interface TriageResult {
  phrases: string[];
  normalized_symptoms: string[];
  specialists: string[];
  recommended_specialists: string[];
  doctors: Doctor[];
}

export const triageApi = {
  /**
   * POST /run_langgraph
   * Runs the specialist-mapping graph: normalizes the patient's symptoms,
   * looks up matching specialties in the database, ranks them, and returns
   * doctors with their next available slot.
   */
  run: (phrases: string[]) =>
    apiFetch<TriageResult>('POST', '/run_langgraph', { phrases }),
};

// ─── Appointments ─────────────────────────────────────────────────────────────
export const appointmentApi = {
  /**
   * POST /appointments — books a slot.
   * Requires a payment_id captured by the payments flow; the server rejects
   * any payment it did not record itself.
   */
  book: (req: {
    patient_id: number;
    doctor_id: number;
    slot_id: number;
    reason: string;
    payment_id?: string | null;
  }) =>
    apiFetch<{ message: string; appointment_id: number }>('POST', '/appointments', req),
};

// ─── Payments (Razorpay) ──────────────────────────────────────────────────────
export const paymentApi = {
  /** POST /payments/create-order — server fixes the amount. */
  createOrder: (amount: number, receipt: string) =>
    apiFetch<{ order_id: string; amount: number; currency: string; key_id: string }>(
      'POST',
      '/payments/create-order',
      { amount, currency: 'INR', receipt },
    ),

  /** POST /payments/verify — records the payment as captured. */
  verify: (razorpay_order_id: string, razorpay_payment_id: string, razorpay_signature: string) =>
    apiFetch<{ verified: boolean; payment_id: string }>('POST', '/payments/verify', {
      razorpay_order_id,
      razorpay_payment_id,
      razorpay_signature,
    }),
};

// ─── Razorpay checkout (loads the SDK once, then opens the modal) ─────────────
declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

let checkoutScript: Promise<boolean> | null = null;

/** Loads checkout.js from Razorpay's CDN exactly once per page session. */
function loadCheckout(): Promise<boolean> {
  if (window.Razorpay) return Promise.resolve(true);
  if (checkoutScript) return checkoutScript;

  checkoutScript = new Promise<boolean>((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
  return checkoutScript;
}

/**
 * Runs the full pay-then-book flow.
 *
 * The amount is never computed on the client for authorisation purposes — the
 * server records the order and re-checks the captured payment at booking time.
 * Returns the verified payment_id, or null if the patient cancelled.
 */
export async function payAndBook(
  doctor: Doctor,
  patientId: number,
  reason: string,
): Promise<{ payment_id: string } | null> {
  if (!(await loadCheckout()) || !window.Razorpay) {
    throw new Error('Could not load the payment window.');
  }

  // Razorpay works in the smallest currency unit.
  const order = await paymentApi.createOrder(doctor.fees * 100, `appt-${doctor.slot_id}`);

  return new Promise((resolve, reject) => {
    const checkout = new window.Razorpay!({
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      order_id: order.order_id,
      name: 'Healthcare Voice Agent',
      description: `${doctor.specialization} consultation`,
      prefill: {},
      theme: { color: '#10b981' },
      handler: async (response: Record<string, string>) => {
        try {
          const verified = await paymentApi.verify(
            response.razorpay_order_id,
            response.razorpay_payment_id,
            response.razorpay_signature,
          );
          await appointmentApi.book({
            patient_id: patientId,
            doctor_id: doctor.doctor_id,
            slot_id: doctor.slot_id,
            reason,
            payment_id: verified.payment_id,
          });
          resolve({ payment_id: verified.payment_id });
        } catch (err) {
          reject(err instanceof Error ? err : new Error('Payment failed.'));
        }
      },
      modal: {
        ondismiss: () => resolve(null),
      },
    });
    checkout.open();
  });
}

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
