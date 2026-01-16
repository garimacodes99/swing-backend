import { create } from "zustand";
import { fetchCloseSnapshot } from "../services/dataService";
import {
    normalizeSnapshotData,
  type NormalizedCandle,
} from "../utils/normalizeSnapshotData";

type CloseState = {
  rows: NormalizedCandle[];
  symbol: string;
  load: (symbol?: string) => Promise<void>;
};

export const useCloseStore = create<CloseState>((set) => ({
  rows: [],
  symbol: "INFY",
  load: async (symbol = "INFY") => {
    const data = await fetchCloseSnapshot();
    const normalized = normalizeSnapshotData(data, "close", symbol);
    set({ rows: normalized, symbol });
  },
}));
