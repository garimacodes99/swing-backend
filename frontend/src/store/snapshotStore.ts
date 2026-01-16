import { create } from "zustand";
import { fetchFinalSnapshot, type FinalSnapshotRow } from "../services/dataService";

interface SnapshotState {
  rows: FinalSnapshotRow[];
  loading: boolean;
  load: () => Promise<void>;
}

export const useSnapshotStore = create<SnapshotState>((set) => ({
  rows: [],
  loading: false,

  load: async () => {
    set({ loading: true });
    const data = await fetchFinalSnapshot();
    set({ rows: data, loading: false });
  },
}));
