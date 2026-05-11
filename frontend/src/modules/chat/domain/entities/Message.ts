export interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  citation?: string;
  imageUrl?: string;
}
