import { ChatStorageRepository } from "../../domain/repositories/ChatStorageRepository";

export class ChatStorageRepositoryImpl implements ChatStorageRepository {
  getItem(name: string): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(name);
  }

  setItem(name: string, value: string): void {
    if (typeof window !== "undefined") {
      localStorage.setItem(name, value);
    }
  }

  removeItem(name: string): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem(name);
    }
  }
}
