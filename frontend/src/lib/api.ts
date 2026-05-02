/**
 * API Client
 * Centralized API communication layer with type safety.
 */

const API_BASE = '/api/v1';

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: SourceReference[];
  confidence_score?: number;
  created_at?: string;
}

export interface SourceReference {
  content: string;
  filename: string;
  page?: number;
  source: string;
  score: number;
  rank: number;
}

export interface ChatResponse {
  message: string;
  session_id: string;
  sources: SourceReference[];
  confidence_score: number;
  follow_up_questions: string[];
  action_result?: Record<string, any>;
  metadata: Record<string, any>;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  source: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  role: string;
  created_at: string;
  updated_at: string;
}

export interface Analytics {
  total_queries: number;
  total_documents: number;
  total_sessions: number;
  avg_confidence: number;
  queries_today: number;
  top_sources: any[];
  recent_queries: any[];
  usage_over_time: { date: string; queries: number }[];
}

export interface SQLResult {
  status: string;
  sql: string;
  results: Record<string, any>[];
  explanation: string;
  row_count: number;
}

class ApiClient {
  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Chat
  async sendMessage(
    message: string,
    sessionId?: string,
    role: string = 'general'
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId, role, stream: false }),
    });
  }

  async sendMessageStream(
    message: string,
    sessionId?: string,
    role: string = 'general',
    onToken: (token: string) => void = () => {},
    onDone: (data: any) => void = () => {},
    onAction: (data: any) => void = () => {},
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId, role, stream: true }),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) throw new Error('No response stream');

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token') onToken(data.data);
            else if (data.type === 'done') onDone(data.data);
            else if (data.type === 'action') onAction(data.data);
            else if (data.type === 'error') onToken(`\n\n⚠️ Error: ${data.data}`);
          } catch {}
        }
      }
    }
  }

  // Documents
  async uploadDocument(file: File): Promise<DocumentInfo> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async getDocuments(): Promise<{ documents: DocumentInfo[]; total: number }> {
    return this.request('/documents');
  }

  async deleteDocument(id: string): Promise<void> {
    await this.request(`/documents/${id}`, { method: 'DELETE' });
  }

  async summarizeDocument(documentId: string): Promise<{ summary: string; key_topics: string[] }> {
    return this.request('/documents/summarize', {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId }),
    });
  }

  async ingestMockData(source: string): Promise<any> {
    return this.request(`/documents/ingest-mock?source=${source}`, { method: 'POST' });
  }

  // Sessions
  async getSessions(): Promise<{ sessions: Session[] }> {
    return this.request('/sessions');
  }

  async createSession(title?: string, role?: string): Promise<Session> {
    return this.request('/sessions', {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Chat', role: role || 'general' }),
    });
  }

  async getSessionHistory(sessionId: string): Promise<{ messages: ChatMessage[] }> {
    return this.request(`/sessions/${sessionId}`);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.request(`/sessions/${sessionId}`, { method: 'DELETE' });
  }

  // SQL
  async executeSQLQuery(query: string): Promise<SQLResult> {
    return this.request('/sql/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  // Analytics
  async getAnalytics(): Promise<Analytics> {
    return this.request('/analytics');
  }
}

export const api = new ApiClient();
