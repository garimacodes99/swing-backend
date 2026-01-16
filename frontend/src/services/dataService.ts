export interface FinalSnapshotRow {
  ticker: string;
  date: string;
  session: "OPEN" | "CLOSE";

  entry_close: number;

  rsi: number;
  atr: number;
  atr_pct: number;

  sma_50: number;
  sma_200: number;

  trend_status: string;
  volatility_class: string;

  past_1m_pct: number;
  past_3m_pct: number;
  past_6m_pct: number;

  swing_score: number;
  swing_label: string;
}

export async function fetchFinalSnapshot(): Promise<FinalSnapshotRow[]> {
  const res = await fetch("/data/final/swing_snapshot_latest.json");
  if (!res.ok) {
    throw new Error("Failed to load final snapshot");
  }
  return res.json();
}
