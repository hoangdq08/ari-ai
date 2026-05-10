import { useQuery } from '@tanstack/react-query';
import { mockFetchArticles } from '../infrastructure/api';
import { useHandbookStore } from './useHandbookStore';

export function useArticles() {
  const searchQuery = useHandbookStore(state => state.searchQuery);
  const activeCategory = useHandbookStore(state => state.activeCategory);

  return useQuery({
    queryKey: ['articles', activeCategory, searchQuery],
    queryFn: () => mockFetchArticles(activeCategory, searchQuery),
    staleTime: 1000 * 60 * 5, // cache for 5 minutes
  });
}
