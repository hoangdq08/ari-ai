import { Article } from "../domain/Article";
import { apiClient } from "../../../core/http/apiClient";

export async function fetchArticles(category: string, search: string): Promise<Article[]> {
  // Luôn gọi xuống Backend, truyền q (có thể rỗng) và category
  const response = await apiClient.get('/handbook/search', {
    params: {
      q: search.trim(),
      category: category,
      limit: 10
    }
  });

  const results = response.data.results || [];

  return results.map((item: any) => ({
    id: item.id,
    title: item.title,
    description: item.content,
    category: item.category,
  }));
}
