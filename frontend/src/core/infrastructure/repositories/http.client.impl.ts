import axios, { AxiosInstance } from 'axios';
import { HttpClientRepository } from '../../domain/repositories/HttpClientRepository';
import { HttpRequestConfig } from '../../domain/models/HttpRequestConfig';

const DEFAULT_API_PREFIX = '/api/v1';

function resolveBaseUrl(rawBaseUrl?: string): string {
  const trimmed = (rawBaseUrl || '').trim();

  if (!trimmed) {
    return DEFAULT_API_PREFIX;
  }

  if (trimmed.startsWith('/')) {
    return trimmed.replace(/\/$/, '');
  }

  try {
    const parsed = new URL(trimmed);
    if (['localhost', '127.0.0.1', '::1'].includes(parsed.hostname)) {
      return DEFAULT_API_PREFIX;
    }

    return `${parsed.origin}${parsed.pathname.replace(/\/$/, '')}`;
  } catch {
    return trimmed;
  }
}

export class HttpClientRepositoryImpl implements HttpClientRepository {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: resolveBaseUrl(process.env.NEXT_PUBLIC_API_URL),
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: HttpRequestConfig): Promise<{ data: T }> {
    return this.client.get<T>(url, config);
  }

  async post<T>(url: string, data?: unknown, config?: HttpRequestConfig): Promise<{ data: T }> {
    return this.client.post<T>(url, data, config);
  }

  async put<T>(url: string, data?: unknown, config?: HttpRequestConfig): Promise<{ data: T }> {
    return this.client.put<T>(url, data, config);
  }

  async delete<T>(url: string, config?: HttpRequestConfig): Promise<{ data: T }> {
    return this.client.delete<T>(url, config);
  }
}
