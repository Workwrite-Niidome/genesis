import { create } from 'zustand';

export type DetailItemType =
  | 'thought'
  | 'event'
  | 'interaction'
  | 'artifact'
  | 'concept'
  | 'memory'
  | 'god_feed';

interface DetailState {
  itemType: DetailItemType | null;
  itemData: any;
  openDetail: (type: DetailItemType, data: any) => void;
  closeDetail: () => void;
}

export const useDetailStore = create<DetailState>((set) => ({
  itemType: null,
  itemData: null,
  openDetail: (type, data) => set({ itemType: type, itemData: data }),
  closeDetail: () => set({ itemType: null, itemData: null }),
}));
