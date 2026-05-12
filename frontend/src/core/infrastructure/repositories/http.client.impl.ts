import axios, { AxiosInstance } from 'axios';
import { HttpClientRepository } from '../../domain/repositories/HttpClientRepository';
import { HttpRequestConfig } from '../../domain/models/HttpRequestConfig';

export class HttpClientRepositoryImpl implements HttpClientRepository {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081/api/v1',
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

  async post<T>(url: string, data?: any, config?: HttpRequestConfig): Promise<{ data: T }> {
    return this.client.post<T>(url, data, config);
  }

  async put<T>(url: string, data?: any, config?: HttpRequestConfig): Promise<{ data: T }> {
    return this.client.put<T>(url, data, config);
  }

  async delete<T>(url: string, config?: HttpRequestConfig): Promise<{ data: T }> {
    return this.client.delete<T>(url, config);
  }
}
