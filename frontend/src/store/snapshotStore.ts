import { create } from "zustand";

interface SnapshotState {
  rows: any[];
  loading: boolean;
  load: () => Promise<void>;
}

export const useSnapshotStore = create<SnapshotState>((set) => ({
  rows: [],
  loading: false,

  load: async () => {
    try {
      set({ loading: true });

      // 1️⃣ Load index.json
      const indexRes = await fetch("/data/index.json");
      if (!indexRes.ok) throw new Error("index.json not found");

      const index = await indexRes.json();
      const latest: string | null = index?.latest ?? null;

      if (!latest) {
        set({ rows: [], loading: false });
        return;
      }

      // 2️⃣ Load CLOSE snapshot
      const snapshotUrl = `/data/close/swing_close_${latest}.json`;
      const res = await fetch(snapshotUrl);

      if (!res.ok) {
        console.error("Snapshot not found:", snapshotUrl);
        set({ rows: [], loading: false });
        return;
      }

      const rawRows = await res.json();

      // 3️⃣ INJECT DATE INTO EACH ROW (CRITICAL FIX)
      const rowsWithDate = rawRows.map((r: any) => ({
        ...r,
        date: latest,          // ← FIX
        Session: "CLOSE",      // optional but useful
      }));

      // 4️⃣ Store rows
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
