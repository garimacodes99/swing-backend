import { useEffect, useState } from "react";
import { useSnapshotStore } from "./store/snapshotStore";

/* ================= TYPES ================= */
type ViewType = "all" | "OPEN" | "CLOSE";
type SortType =
  | "none"
  | "score_desc"
  | "score_asc"
  | "rsi_desc"
  | "rsi_asc";

/* ================= HELPERS ================= */
function scoreColor(score: number | null) {
  if (score === null) return "";
  if (score >= 20)
    return "text-green-700 bg-green-50 px-2 py-0.5 rounded-full";
  if (score >= 15) return "text-green-600";
  if (score >= 8) return "text-yellow-600";
  return "text-red-600";
}

function toDate(d: string) {
  return new Date(d + "T00:00:00");
}

export default function App() {
  const { rows, load } = useSnapshotStore();

  /* ================= STATE ================= */
  const [view, setView] = useState<ViewType>("all");
  const [sortBy, setSortBy] = useState<SortType>("none");

  const [minScore, setMinScore] = useState(0);
  const [rsiMin, setRsiMin] = useState(0);
  const [rsiMax, setRsiMax] = useState(100);

  const [selectedDate, setSelectedDate] = useState<string>("all");
  const [fromDate, setFromDate] = useState("");
  const [toDateRange, setToDateRange] = useState("");

  /* ================= LOAD ================= */
  useEffect(() => {
    load();
  }, [load]);

  /* ================= DATES ================= */
  const availableDates = Array.from(new Set(rows.map((r) => r.date)))
    .filter(Boolean)
    .sort()
    .reverse();

  const latestDate = availableDates[0];
  const yesterdayDate = availableDates[1];

  /* ================= FILTER ================= */
  const filteredRows = rows
    .filter((r) => (view === "all" ? true : r.session === view))
    .filter((r) =>
      selectedDate === "all" ? true : r.date === selectedDate
    )
    .filter((r) => {
      if (!fromDate && !toDateRange) return true;
      const d = toDate(r.date);
      if (fromDate && d < toDate(fromDate)) return false;
      if (toDateRange && d > toDate(toDateRange)) return false;
      return true;
    })
    .filter((r) => (r.swing_score ?? 0) >= minScore)
    .filter((r) => {
      if (r.rsi === null) return true;
      return r.rsi >= rsiMin && r.rsi <= rsiMax;
    });

  /* ================= SORT ================= */
  const sortedRows = [...filteredRows].sort((a, b) => {
    if (sortBy === "score_desc")
      return (b.swing_score ?? 0) - (a.swing_score ?? 0);
    if (sortBy === "score_asc")
      return (a.swing_score ?? 0) - (b.swing_score ?? 0);
    if (sortBy === "rsi_desc") return (b.rsi ?? 0) - (a.rsi ?? 0);
    if (sortBy === "rsi_asc") return (a.rsi ?? 0) - (b.rsi ?? 0);
    return 0;
  });

  /* ================= KPI ================= */
  const uniqueStocks = new Set(sortedRows.map((r) => r.ticker)).size;

  const avgSwingScore =
    sortedRows.length > 0
      ? (
          sortedRows.reduce(
            (sum, r) => sum + (r.swing_score ?? 0),
            0
          ) / sortedRows.length
        ).toFixed(2)
      : "0.00";

  const strongCount = sortedRows.filter(
    (r) => (r.swing_score ?? 0) >= 15
  ).length;

  const highConviction = sortedRows.filter(
    (r) => (r.swing_score ?? 0) >= 20
  ).length;

  /* ================= UI ================= */
  return (
    /* ===== BLUE BACKGROUND ===== */
    <div className="min-h-screen bg-blue-300 p-8">



      {/* ===== FLOATING DASHBOARD CARD ===== */}
      <div className="max-w-[1600px] mx-auto bg-slate-50 rounded-2xl shadow-2xl p-8 relative -top-6">

        

        <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">
          Swing Trading Platform
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Quantitative signal screening & risk-filtered opportunities
        </p>
        </div>


        {/* ===== TOP CONTROLS ===== */}
        <div className="mb-6 flex items-start justify-between gap-6">
          {/* LEFT */}
          <div className="flex flex-wrap items-center gap-6">
            {/* SESSION */}
            <div className="flex gap-2">
              {(["all", "OPEN", "CLOSE"] as ViewType[]).map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                    view === v
                      ? "bg-blue-600 text-white shadow"
                      : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  {v === "all" ? "All" : v}
                </button>
              ))}
            </div>

            {/* SORT */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortType)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="none">Sort: None</option>
              <option value="score_desc">Score ↓</option>
              <option value="score_asc">Score ↑</option>
              <option value="rsi_desc">RSI ↓</option>
              <option value="rsi_asc">RSI ↑</option>
            </select>

            {/* MIN SCORE */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-mediu m text-gray-700">
                Min Score
              </span>
              <input
                type="number"
                value={minScore}
                onChange={(e) => setMinScore(+e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 w-24 text-sm bg-white shadow-sm
                focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* RSI */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                RSI
              </span>
              <input
                type="number"
                value={rsiMin}
                onChange={(e) => setRsiMin(+e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 w-20 text-sm bg-white shadow-sm"
              />
              <span className="text-gray-500">–</span>
              <input
                type="number"
                value={rsiMax}
                onChange={(e) => setRsiMax(+e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 w-20 text-sm bg-white shadow-sm"
              />
            </div>
          </div>

          {/* RIGHT (DATES) */}
          <div className="flex flex-col items-end gap-3">
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setSelectedDate(latestDate);
                  setFromDate("");
                  setToDateRange("");
                }}
                className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 text-sm font-medium hover:bg-gray-100 shadow-sm"
              >
                Today
              </button>

              <button
                onClick={() => {
                  setSelectedDate(yesterdayDate);
                  setFromDate("");
                  setToDateRange("");
                }}
                className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 text-sm font-medium hover:bg-gray-100 shadow-sm"
              >
                Yesterday
              </button>

              <button
                onClick={() => {
                  setSelectedDate("all");
                  setFromDate("");
                  setToDateRange("");
                }}
                className="px-3 py-1.5 rounded-lg bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 text-sm font-medium"
              >
                Clear
              </button>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="date"
                value={fromDate}
                onChange={(e) => {
                  setSelectedDate("all");
                  setFromDate(e.target.value);
                }}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm"
              />
              <span className="text-gray-500">–</span>
              <input
                type="date"
                value={toDateRange}
                onChange={(e) => {
                  setSelectedDate("all");
                  setToDateRange(e.target.value);
                }}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm"
              />
            </div>
          </div>
        </div>

        {/* ===== KPI ===== */}
        <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI label="Unique Stocks" value={uniqueStocks} />
          <KPI label="Avg Swing Score" value={avgSwingScore} />
          <KPI label="Strong Signals (≥15)" value={strongCount} green />
          <KPI label="High Conviction (≥20)" value={highConviction} green />
        </div>

        {/* ===== TABLE ===== */}
        <div className="bg-white rounded-xl shadow-md border border-slate-200 overflow-x-auto">
          <table className="w-full text-sm text-center">
            <thead className="bg-gray-100 text-gray-700">
              <tr>
                {[
                  "S.No",
                  "Ticker",
                  "Date",
                  "Session",
                  "Close Price",
                  "RSI",
                  "ATR %",
                  "Trend",
                  "Volatility",
                  "Swing Score",
                  "Label",
                ].map((h) => (
                  <th
                    key={h}
                    className="p-3 text-xs font-semibold uppercase tracking-wide"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {sortedRows.map((r, i) => (
                <tr
                  key={`${r.ticker}-${r.date}-${r.session}`}
                  className={`border-t hover:bg-blue-50 ${
                    i % 2 === 0 ? "bg-white" : "bg-gray-50"
                  }`}
                >
                  <td className="p-2">{i + 1}</td>
                  <td className="p-2 font-semibold text-blue-700 cursor-pointer hover:underline">
                    {r.ticker}
                  </td>
                  <td className="p-2">{r.date}</td>
                  <td className="p-2">{r.session}</td>
                  <td className="p-2">{r.entry_close ?? "—"}</td>
                  <td className="p-2">{r.rsi?.toFixed(2) ?? "—"}</td>
                  <td className="p-2">{r.atr_pct?.toFixed(2) ?? "—"}</td>
                  <td className="p-2">{r.trend_status ?? "—"}</td>
                  <td className="p-2">{r.volatility_class ?? "—"}</td>
                  <td className={`p-2 font-bold ${scoreColor(r.swing_score)}`}>
                    {r.swing_score ?? "—"}
                  </td>
                  <td className="p-2">{r.swing_label ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}

/* ================= KPI COMPONENT ================= */
function KPI({
  label,
  value,
  green,
}: {
  label: string;
  value: any;
  green?: boolean;
}) {
  return (
    <div
      className="
        bg-white
        rounded-xl
        border border-slate-200
        shadow-sm
        p-5
        text-center
        transition-all
        duration-200
        ease-out
        hover:-translate-y-1
        hover:shadow-lg
        hover:border-blue-300
        hover:bg-blue-50/40
        cursor-default
      "
    >
      <div className="text-sm font-medium uppercase tracking-wide text-slate-600 mb-2">
      {label}
      </div>


      <div
        className={`text-3xl font-extrabold transition-colors duration-200 ${
          green ? "text-green-600" : "text-slate-800"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

