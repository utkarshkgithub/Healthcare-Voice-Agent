// API Base URL from environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// API Client with authentication
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getHeaders(): HeadersInit {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }
}

// Create singleton instance
export const api = new ApiClient(API_BASE_URL);

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/api/auth/login', { email, password }),
  
  signup: (name: string, email: string, password: string) =>
    api.post('/api/auth/signup', { name, email, password }),
  
  logout: () => {
    localStorage.removeItem('token');
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: () => api.get('/api/dashboard/stats'),
  getConsultations: () => api.get('/api/consultations/recent'),
  getAppointments: () => api.get('/api/appointments/upcoming'),
  getHealthMetrics: () => api.get('/api/health/metrics'),
};

// Chat API
export const chatApi = {
  sendMessage: (message: string) =>
    api.post('/api/chat/send', { message }),
  
  getHistory: () => api.get('/api/chat/history'),
  
  getSession: (sessionId: number) =>
    api.get(`/api/chat/sessions/${sessionId}`),
};

// WebSocket for real-time chat
export const createChatWebSocket = (onMessage: (data: unknown) => void) => {
  const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
  const token = localStorage.getItem('token');
  
  const ws = new WebSocket(`${WS_URL}?token=${token}`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };
  
  return ws;
};
