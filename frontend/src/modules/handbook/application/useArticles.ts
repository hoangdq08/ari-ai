import { useQuery } from '@tanstack/react-query';
import { useHandbookStore } from './useHandbookStore';
import { IHandbookApi } from '../domain/interfaces/IHandbookApi';

export function useArticles(api: IHandbookApi) {
  const searchQuery = useHandbookStore(state => state.searchQuery);
  const activeCategory = useHandbookStore(state => state.activeCategory);

  return useQuery({
    queryKey: ['articles', activeCategory, searchQuery],
    queryFn: () => api.fetchArticles(activeCategory, searchQuery),
    staleTime: 1000 * 60 * 5, // cache for 5 minutes
  });
}
