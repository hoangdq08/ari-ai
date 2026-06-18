import { HttpRequestConfig } from "../models/HttpRequestConfig";

export interface HttpClientRepository {
  get<T>(url: string, config?: HttpRequestConfig): Promise<{ data: T }>;
  post<T>(url: string, data?: unknown, config?: HttpRequestConfig): Promise<{ data: T }>;
  put<T>(url: string, data?: unknown, config?: HttpRequestConfig): Promise<{ data: T }>;
  delete<T>(url: string, config?: HttpRequestConfig): Promise<{ data: T }>;
}
