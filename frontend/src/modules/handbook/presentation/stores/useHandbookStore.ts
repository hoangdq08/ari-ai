import { create } from 'zustand';

interface HandbookState {
  searchQuery: string;
  activeCategory: string;
  setSearchQuery: (query: string) => void;
  setActiveCategory: (category: string) => void;
}

export const useHandbookStore = create<HandbookState>((set) => ({
  searchQuery: "",
  activeCategory: "Tất cả",
  setSearchQuery: (query) => set({ searchQuery: query }),
  setActiveCategory: (category) => set({ activeCategory: category }),
}));
