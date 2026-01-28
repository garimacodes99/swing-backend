import { create } from "zustand";
import { fetchFinalSnapshot } from "../services/dataService";
import {
  normalizeSnapshotData,
  type NormalizedCandle,
} from "../utils/normalizeSnapshotData";

/**
 * Extend NormalizedCandle with Entry Engine fields
 * (DO NOT modify normalizeSnapshotData.ts)
 */
export type CloseRow = NormalizedCandle & {
  Entry_Signal: boolean;
  Entry_Momentum_Turn: boolean;
  Entry_Volatility_Expansion: boolean;
  Entry_Structure_Confirmation: boolean;
};

type CloseState = {
  rows: CloseRow[];
  symbol: string;
  load: (symbol?: string) => Promise<void>;
};

export const useCloseStore = create<CloseState>((set) => ({
  rows: [],
  symbol: "INFY",

  load: async (symbol = "INFY") => {
    // ✅ Correct data source
    const raw = await fetchFinalSnapshot();

    // ✅ Filter CLOSE session + symbol
    const closeRows = raw.filter(
      (r) => r.session === "CLOSE" && r.ticker === symbol
    );

    // ✅ Normalize and extend
    const normalized = normalizeSnapshotData(
      closeRows,
      "close",
      symbol
    ) as CloseRow[];

    set({ rows: normalized, symbol });
  },
}));
