/**
 * API client for AEKA backend.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // ─── Documents ─────────────────────────────────────────────────────
  async listDocuments(skip = 0, limit = 50) {
    return this.request<{ documents: any[]; total: number }>(
      `/api/v1/documents/?skip=${skip}&limit=${limit}`
    );
  }

  async uploadDocument(file: File, strategy = 'recursive') {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${this.baseUrl}/api/v1/documents/upload?chunk_strategy=${strategy}`,
      { method: 'POST', body: formData }
    );

    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  }

  async deleteDocument(id: string) {
    await fetch(`${this.baseUrl}/api/v1/documents/${id}`, { method: 'DELETE' });
  }

  // ─── Search ────────────────────────────────────────────────────────
  async search(query: string, topK = 10) {
    return this.request<any>('/api/v1/search/', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    });
  }

  // ─── Chat ──────────────────────────────────────────────────────────
  async listSessions() {
    return this.request<any[]>('/api/v1/chat/sessions');
  }

  async getSessionMessages(sessionId: string) {
    return this.request<any[]>(`/api/v1/chat/sessions/${sessionId}/messages`);
  }

  // ─── Review Queue ──────────────────────────────────────────────────
  async getReviewQueue() {
    return this.request<{ items: any[] }>('/api/v1/review/queue');
  }

  async updateReviewItem(id: string, status: string, editedAnswer?: string) {
    return this.request<any>(`/api/v1/review/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, edited_answer: editedAnswer }),
    });
  }

  // ─── Metrics ───────────────────────────────────────────────────────
  async getMetrics(timeRange = '7d') {
    return this.request<any>(`/api/v1/metrics?range=${timeRange}`);
  }
}

export const api = new ApiClient(BASE_URL);
