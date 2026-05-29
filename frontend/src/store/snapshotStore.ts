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

      if (!targetDate) {
        console.log("No date provided to load(), fetching latest from index.json");
        const indexRes = await fetch("/close/index.json");
        if (indexRes.ok) {
          const index = await indexRes.json();
          targetDate = index.latest;
          console.log("Latest date from index:", targetDate);
        } else {
          console.error("Failed to fetch /close/index.json", indexRes.status);
        }
      }

      if (!targetDate) {
        console.warn("Could not determine target date, aborting load.");
        set({ rows: [], loading: false });
        return;
      }

      const snapshotUrl = `/close/swing_close_${targetDate}.json`;
      console.log("Attempting to fetch snapshot:", snapshotUrl);

      const res = await fetch(snapshotUrl);

      if (!res.ok) {
        console.error(`Snapshot fetch failed for ${targetDate}. Status: ${res.status} ${res.statusText}`);
        // If we get an HTML response (likely a 404 fallback), log a snippet for debugging
        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("text/html")) {
          console.error("Received HTML instead of JSON. Ensure the file exists in public/close/");
        }
        set({ rows: [], loading: false });
        return;
      }

      const rawRows = await res.json();
      console.log(`Successfully loaded ${rawRows.length} rows for ${targetDate}`);

      const rowsWithDate = rawRows.map((r: any) => {
        const distStr = r["Distance %"] || "0";
        const distNum = parseFloat(String(distStr).replace("%", ""));

        return {
          Ticker: r["Ticker"],
          LTP: r["LTP"],
          "Trend Status": r["Trend Status"],
          "Momentum Status": r["Momentum Status"],
          "Volume Strength": r["Volume Strength"],
          "Swing Score": r["Swing Score"],
          "Setup Type": r["Setup Type"],
          "Distance Status": r["Distance Status"],
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
      console.error("Failed to process snapshot data:", err);
      set({ rows: [], loading: false });
    }
  },
}));