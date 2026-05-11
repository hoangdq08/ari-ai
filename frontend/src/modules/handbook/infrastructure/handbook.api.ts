import { Article } from "../domain/entities/Article";
import { IHandbookApi } from "../domain/interfaces/IHandbookApi";
import { apiClient } from "../../../core/http/apiClient";

class HandbookApiImpl implements IHandbookApi {
  async fetchArticles(category: string, search: string): Promise<Article[]> {
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
}

export const handbookApi = new HandbookApiImpl();
