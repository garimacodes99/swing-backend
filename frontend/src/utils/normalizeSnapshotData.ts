export type SnapshotType = "open" | "close";

export type NormalizedCandle = {
  id: number;
  symbol: string;
  snapshot: SnapshotType;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;

  rsi?: number;
  volatility_pct?: number;
  final_swing_score?: number;
};


export function normalizeSnapshotData(
  raw: any[],
  snapshot: SnapshotType,
  symbol = "UNKNOWN"
): NormalizedCandle[] {
  return raw.map((r, idx) => ({
  id: idx,
  symbol,
  snapshot,
  open: r.Open ?? 0,
  high: r.High ?? 0,
  low: r.Low ?? 0,
  close: r.Close ?? 0,
  volume: r.Volume ?? 0,

  rsi: r.RSI ?? null,
  volatility_pct: r["Volatility%"] ?? null,
  final_swing_score: r["FinalSwingScore"] ?? null,
}));
}
