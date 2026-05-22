import { create } from "zustand";

interface SnapshotState {
  rows: any[];
  loading: boolean;
  load: (date?: string) => Promise<void>;
}

export const useSnapshotStore = create<SnapshotState>((set) => ({
  rows: [],
  loading: false,

  load: async (date?: string) => {
    try {
      set({ loading: true });

      let targetDate = date;

      // 1. If no date provided, fetch index.json to find the latest
      if (!targetDate) {
        const indexRes = await fetch("/data/index.json");
        if (indexRes.ok) {
          const index = await indexRes.json();
          targetDate = index.latest;
        }
      }

      if (!targetDate) {
        set({ rows: [], loading: false });
        return;
      }

      // 2. Load the specific snapshot for the target date
      const snapshotUrl = `/data/close/swing_close_${targetDate}.json`;
      console.log("Fetching snapshot from:", snapshotUrl);
      const res = await fetch(snapshotUrl);

      if (!res.ok) {
        console.error("Snapshot not found at:", snapshotUrl);
        set({ rows: [], loading: false });
        return;
      }

      const rawRows = await res.json();
      console.log("Raw rows loaded:", rawRows.length, "Sample:", rawRows[0]);

      // 3. Normalize keys: JSON has "RSI 14", "Weighted Avg", "Distance %"
      //    but frontend expects RSI_14, Weighted_Avg, Dist_Weighted_Avg_PCT
      const rowsWithDate = rawRows.map((r: any) => {
        // Parse Distance % string like "-5.25%" or "+2.65%" into a number
        const distStr = r["Distance %"] || "0";
        const distNum = parseFloat(distStr.replace('%', ''));

        return {
          Ticker: r["Ticker"],
          LTP: r["LTP"],
          RSI_14: r["RSI 14"],
          Weighted_Avg: r["Weighted Avg"],
          Dist_Weighted_Avg_PCT: isNaN(distNum) ? 0 : distNum,
          Google_Finance: r["Google Finance"],
          date: targetDate,
        };
      });

      set({
        rows: rowsWithDate,
        loading: false,
      });

    } catch (err) {
      console.error("Snapshot load failed:", err);
      set({ rows: [], loading: false });
    }
  },
}));
