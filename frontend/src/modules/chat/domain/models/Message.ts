export interface ChatSource {
  title: string;
  url: string | null;
  reliabilityLevel: string | null;
}

export interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  citation?: string;
  imageUrl?: string;
  sources?: ChatSource[];
}
