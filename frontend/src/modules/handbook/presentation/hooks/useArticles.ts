import { useQuery } from '@tanstack/react-query';
import { useHandbookStore } from '../stores/useHandbookStore';
import { useDI } from '@/shared/hooks/useDI';

export function useArticles() {
  const { handbookApiRepository } = useDI();
  const searchQuery = useHandbookStore(state => state.searchQuery);
  const activeCategory = useHandbookStore(state => state.activeCategory);

  return useQuery({
    queryKey: ['articles', activeCategory, searchQuery],
    queryFn: () => handbookApiRepository.fetchArticles(activeCategory, searchQuery),
    staleTime: 1000 * 60 * 5, // cache for 5 minutes
  });
}
