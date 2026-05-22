import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useSnapshotStore } from "./store/snapshotStore";
import {
  Calendar, Search, Download, ChevronDown,
  ExternalLink, ChevronLeft, ChevronRight, BarChart3, X, RotateCcw
} from "lucide-react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
} from "@tanstack/react-table";
import type { SortingState } from "@tanstack/react-table";

/* ────────────────────────────────────────────────────────────
   TAG BADGE — compact pill with color coding
   ──────────────────────────────────────────────────────────── */
const tagColors: Record<string, string> = {
  LCAP: 'bg-blue-500/15 text-blue-300 border-blue-500/25',
  MCAP: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/25',
  SCAP: 'bg-slate-500/15 text-slate-300 border-slate-600/30',
  MICAP: 'bg-slate-600/15 text-slate-400 border-slate-600/20',
  N50: 'bg-amber-500/15 text-amber-300 border-amber-500/25',
  N100: 'bg-amber-500/10 text-amber-400/80 border-amber-600/20',
  LEADER: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  GROWTH: 'bg-green-500/15 text-green-300 border-green-600/25',
  EXPORT: 'bg-violet-500/15 text-violet-300 border-violet-500/25',
  TECH: 'bg-sky-500/15 text-sky-300 border-sky-500/25',
  PHARMA: 'bg-rose-500/12 text-rose-300 border-rose-500/20',
  BANKX: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/25',
  INFRA: 'bg-orange-500/12 text-orange-300 border-orange-500/20',
  DEFX: 'bg-red-500/12 text-red-300 border-red-500/20',
  DUO30: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/25',
};

const TagPill = ({ label }: { label: string }) => {
  const color = tagColors[label] || 'bg-slate-700/20 text-slate-400 border-slate-600/30';
  return (
    <span className={`inline-block px-2 py-[2.5px] rounded text-[12.5px] font-semibold tracking-wide border ${color} whitespace-nowrap`}>
      {label}
    </span>
  );
};

/* ────────────────────────────────────────────────────────────
   FILTER INPUT — reusable styled input component
   ──────────────────────────────────────────────────────────── */
const FilterInput = ({ label, value, onChange, placeholder, type = "text", width = "w-16" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string; width?: string;
}) => (
  <div className="flex items-center gap-2.5">
    <span className="text-xs uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">{label}</span>
    <input
      type={type}
      className={`bg-slate-800 border border-slate-700/60 rounded-md hover:border-slate-500 focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/20 outline-none px-3 py-2 ${width} text-slate-200 font-mono text-sm text-center placeholder:text-slate-500 transition-all shadow-sm`}
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
    />
  </div>
);

const FilterSelect = ({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[];
}) => (
  <div className="flex items-center gap-2.5">
    <span className="text-xs uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">{label}</span>
    <select
      className={`bg-slate-800 border rounded-md outline-none px-3 py-2 text-sm cursor-pointer font-mono transition-all hover:border-slate-500 shadow-sm ${value !== 'All' ? 'border-blue-500/50 text-blue-300 bg-blue-500/5' : 'border-slate-700/60 text-slate-300'
        } focus:border-blue-500/60`}
      value={value}
      onChange={e => onChange(e.target.value)}
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

/* ────────────────────────────────────────────────────────────
   MAIN TERMINAL COMPONENT
   ──────────────────────────────────────────────────────────── */

// ── Market cap classification by tags ──
const getMarketCapFromTags = (tagList: string[]): string => {
  if (tagList.includes('LCAP')) return 'Large';
  if (tagList.includes('MCAP')) return 'Mid';
  if (tagList.includes('SCAP')) return 'Small';
  if (tagList.includes('MICAP')) return 'Micro';
  return 'Unknown';
};

const columnHelper = createColumnHelper<any>();

export default function SwingTerminalDark() {
  const { rows, load } = useSnapshotStore();

  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [scores, setScores] = useState<{ ticker?: string; Tickers?: string; Score?: number; score?: number; tags?: string }[]>([]);

  // Filter State
  const [searchTerm, setSearchTerm] = useState("");
  const [exactScore, setExactScore] = useState("");
  const [minDist, setMinDist] = useState("");
  const [maxDist, setMaxDist] = useState("");
  const [rsiZone, setRsiZone] = useState("All");
  const [marketCap, setMarketCap] = useState("All");
  const [trend, setTrend] = useState("All");
  const [tagsInput, setTagsInput] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: 'Score', desc: true }]);

  const [isCalOpen, setIsCalOpen] = useState(false);
  const calRef = useRef<HTMLDivElement>(null);

  const hasActiveFilters = searchTerm || exactScore || minDist || maxDist || rsiZone !== "All" || marketCap !== "All" || trend !== "All" || tagsInput;

  const resetFilters = useCallback(() => {
    setSearchTerm(""); setExactScore(""); setMinDist(""); setMaxDist("");
    setRsiZone("All"); setMarketCap("All"); setTrend("All"); setTagsInput("");
  }, []);

  // ── Data Loading ──
  useEffect(() => {
    // Primary index for trading snapshots
    fetch("/close/index.json")
      .then(r => r.json())
      .then(data => {
        const dList = data.dates.map((d: { date: string }) => d.date);
        setDates(dList);
        if (data.latest && !selectedDate) {
          console.log("Setting initial date from index:", data.latest);
          setSelectedDate(data.latest);
        }
      })
      .catch(err => console.error("Error loading index from /close/index.json:", err));

    fetch("/data/scores.json")
      .then(r => r.json())
      .then((data: { ticker?: string; Tickers?: string; Score?: number; score?: number; tags?: string }[]) => setScores(data))
      .catch(err => console.error("Error loading scores:", err));
  }, []);

  useEffect(() => {
    if (selectedDate) load(selectedDate);
  }, [selectedDate, load]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (calRef.current && !calRef.current.contains(e.target as Node)) setIsCalOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [setIsCalOpen]);

  // ── Calendar ──
  const calendarData = useMemo(() => {
    if (!selectedDate) return { month: '', year: 0, daysInMonth: 0, firstDayOfMonth: 0 };
    const d = new Date(selectedDate);
    return {
      month: d.toLocaleString('default', { month: 'long' }),
      year: d.getFullYear(),
      firstDayOfMonth: new Date(d.getFullYear(), d.getMonth(), 1).getDay(),
      daysInMonth: new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate(),
    };
  }, [selectedDate]);

  // ── Score Map ──
  const scoreMap = useMemo(() => {
    const map: Record<string, { score: number; tags: string; tagList: string[] }> = {};
    scores.forEach(s => {
      const ticker = (s.ticker || s.Tickers || "").toUpperCase();
      if (!ticker) return;
      const rawTags = (s.tags || "").toUpperCase();
      const tagList = rawTags.split('|').map(t => t.trim()).filter(Boolean);
      map[ticker] = { score: s.score ?? s.Score ?? 0, tags: rawTags, tagList };
    });
    return map;
  }, [scores]);

  // ── All unique tags for reference ──
  const allUniqueTags = useMemo(() => {
    const set = new Set<string>();
    Object.values(scoreMap).forEach(v => v.tagList.forEach(t => set.add(t)));
    return Array.from(set).sort();
  }, [scoreMap]);

  // ── Filtered Data & Score Counts ──
  const { filteredData, scoreCounts } = useMemo(() => {
    let baseData = [...rows].filter(r => r.date === selectedDate);

    // Merge score + tags into each row
    baseData = baseData.map(r => {
      const meta = scoreMap[(r.Ticker || '').toUpperCase()];
      return { ...r, Score: meta?.score, Tags: meta?.tags || '', TagList: meta?.tagList || [] };
    });

    // Calculate score counts for all available data on this date
    const counts: Record<number, number> = {};
    baseData.forEach(r => {
      if (r.Score !== undefined) {
        counts[r.Score] = (counts[r.Score] || 0) + 1;
      }
    });

    let data = [...baseData];

    // Search
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      data = data.filter(r => r.Ticker?.toLowerCase().includes(q));
    }

    // Exact Score
    if (exactScore !== "") {
      const n = Number(exactScore);
      if (!isNaN(n)) data = data.filter(r => r.Score === n);
    }

    // Distance % range
    if (minDist !== "") {
      const n = Number(minDist);
      if (!isNaN(n)) data = data.filter(r => (r.Dist_Weighted_Avg_PCT ?? -Infinity) >= n);
    }
    if (maxDist !== "") {
      const n = Number(maxDist);
      if (!isNaN(n)) data = data.filter(r => (r.Dist_Weighted_Avg_PCT ?? Infinity) <= n);
    }

    // RSI Zone
    if (rsiZone !== "All") {
      data = data.filter(r => {
        const rsi = r.RSI_14 ?? 50;
        if (rsiZone === "Healthy") return rsi >= 40 && rsi <= 60;
        if (rsiZone === "Oversold") return rsi < 40;
        if (rsiZone === "Overbought") return rsi > 60;
        return true;
      });
    }

    // Market Cap (based on tags LCAP/MCAP/SCAP/MICAP)
    if (marketCap !== "All") {
      data = data.filter(r => getMarketCapFromTags(r.TagList || []) === marketCap);
    }

    // Trend (Bullish/Bearish)
    if (trend !== "All") {
      data = data.filter(r => {
        const d = r.Dist_Weighted_Avg_PCT ?? 0;
        return trend === "Bullish" ? d > 0 : d <= 0;
      });
    }

    // Tags filter (pipe-separated input)
    if (tagsInput.trim()) {
      const filterTags = tagsInput.toUpperCase().split(',').map(s => s.trim()).filter(Boolean);
      data = data.filter(r => {
        const rowTags = r.TagList || [];
        return filterTags.some(ft => rowTags.some((rt: string) => rt.includes(ft)));
      });
    }

    return { filteredData: data, scoreCounts: counts };
  }, [rows, selectedDate, searchTerm, exactScore, minDist, maxDist, rsiZone, marketCap, trend, tagsInput, scoreMap]);

  // ── TanStack Table ──

  const columns = useMemo(() => [
    columnHelper.accessor((_row, i) => i + 1, {
      id: 'sno',
      header: '#',
      cell: info => <span className="text-slate-600 font-mono text-[11px]">{info.getValue()}</span>,
      size: 44,
      enableSorting: false,
    }),

    columnHelper.accessor('Ticker', {
      header: 'ASSET',
      cell: info => {
        const ticker = info.getValue() || '';
        return (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-600/40 flex items-center justify-center text-[10px] font-bold text-slate-300 tracking-tight shrink-0">
              {ticker.slice(0, 2)}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-bold text-[14px] text-slate-100 tracking-wide truncate">{ticker}</span>
              <span className="text-[10px] text-slate-500 font-medium tracking-wider truncate">NSE • EQUITY</span>
            </div>
          </div>
        );
      },
      size: 220,
    }),

    columnHelper.accessor('LTP', {
      header: () => <div className="text-right w-full">LTP</div>,
      cell: info => (
        <div className="text-right font-mono text-[14px] text-slate-200 font-medium tabular-nums">
          ₹{(info.getValue() || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
      ),
      size: 120,
    }),

    columnHelper.accessor('Score', {
      header: () => <div className="text-right w-full">SCORE</div>,
      cell: info => {
        const val = info.getValue();
        if (val === undefined || val === null) return <div className="text-right font-mono text-[14px] text-slate-600">—</div>;
        let bg = 'bg-slate-700/30 text-slate-300';
        if (val >= 8) bg = 'bg-emerald-500/15 text-emerald-400 font-bold';
        else if (val >= 6) bg = 'bg-blue-500/10 text-blue-300';
        else if (val <= 4) bg = 'bg-red-500/12 text-red-400';
        return (
          <div className="flex justify-end">
            <span className={`inline-flex items-center justify-center w-8 h-6 rounded ${bg} font-mono text-[14px] tabular-nums`}>
              {val}
            </span>
          </div>
        );
      },
      sortingFn: "basic",
      size: 80,
    }),

    columnHelper.accessor('RSI_14', {
      header: () => <div className="text-right w-full">RSI</div>,
      cell: info => {
        const val = info.getValue() || 0;
        let color = 'text-slate-400';
        if (val < 40) color = 'text-terminal-red';
        else if (val > 60) color = 'text-terminal-green';
        return <div className={`text-right font-mono text-[14px] tabular-nums ${color}`}>{val.toFixed(1)}</div>;
      },
      size: 80,
    }),

    columnHelper.accessor('Weighted_Avg', {
      header: () => <div className="text-right w-full">W.AVG</div>,
      cell: info => (
        <div className="text-right font-mono text-[14px] text-slate-500 tabular-nums">
          ₹{(info.getValue() || 0).toLocaleString('en-IN', { minimumFractionDigits: 0 })}
        </div>
      ),
      size: 110,
    }),

    columnHelper.accessor('Dist_Weighted_Avg_PCT', {
      header: () => <div className="text-right w-full">DIST %</div>,
      cell: info => {
        const val = info.getValue() || 0;
        const isPos = val > 0;
        return (
          <div className={`text-right font-mono text-[14px] font-semibold tabular-nums ${isPos ? 'text-terminal-green' : 'text-terminal-red'}`}>
            {isPos ? '+' : ''}{val.toFixed(2)}%
          </div>
        );
      },
      size: 100,
    }),

    columnHelper.accessor('Tags', {
      header: 'TAGS',
      cell: info => {
        const tagsStr = info.getValue() || '';
        if (!tagsStr) return <span className="text-slate-700">—</span>;
        const tags = tagsStr.split('|').map((t: string) => t.trim()).filter(Boolean);
        const visible = tags.slice(0, 5);
        const extra = tags.length - 5;
        return (
          <div className="flex gap-1.5 flex-wrap items-center">
            {visible.map((t: string, i: number) => <TagPill key={i} label={t} />)}
            {extra > 0 && <span className="text-[10px] text-slate-500 font-mono">+{extra}</span>}
          </div>
        );
      },
      enableSorting: false,
      size: 300,
    }),

    columnHelper.display({
      id: 'link',
      header: () => <div className="text-center w-full">LINK</div>,
      cell: info => (
        <div className="flex justify-center">
          <a
            href={`https://www.google.com/finance/quote/${info.row.original.Ticker}:NSE`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-slate-800/60 border border-slate-700/40 text-slate-500 hover:text-blue-400 hover:border-blue-500/40 hover:bg-blue-500/10 transition-all"
          >
            <ExternalLink size={20} />
          </a>
        </div>
      ),
      size: 70,
    }),
  ], []);

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // ── Export CSV ──
  const handleExport = () => {
    const csv = [
      ['Ticker', 'LTP', 'Score', 'RSI 14', 'Weighted Avg', 'Distance %', 'Tags'].join(','),
      ...filteredData.map(r => [
        r.Ticker, r.LTP, r.Score ?? '', (r.RSI_14 || 0).toFixed(1), r.Weighted_Avg,
        (r.Dist_Weighted_Avg_PCT || 0).toFixed(2), `"${r.Tags || ''}"`
      ].join(','))
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = `swing-signals-${selectedDate}.csv`;
    a.click();
  };

  /* ══════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen h-screen bg-slate-950 text-terminal-text flex flex-col font-sans selection:bg-terminal-green/20 selection:text-terminal-green overflow-hidden">

      {/* ─── HEADER ─── */}
      <header className="h-11 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-5 z-30 shrink-0">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2.5">
            <BarChart3 size={18} className="text-terminal-green" />
            <h1 className="text-sm font-bold text-slate-100 tracking-wider">
              SWING<span className="text-slate-500 font-mono font-normal">//LOGIC</span>
            </h1>
          </div>
          <div className="h-4 w-px bg-[#1c2030]" />
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-terminal-green animate-pulse" />
            <span className="text-[10px] font-mono text-terminal-green/80 tracking-widest uppercase">Live</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Calendar Picker */}
          <div className="relative" ref={calRef}>
            <button onClick={() => setIsCalOpen(!isCalOpen)} className="flex items-center gap-2.5 px-3 py-1.5 bg-slate-800 border border-slate-700/60 hover:border-slate-500/50 rounded-md text-[12px] font-mono transition-all text-slate-300">
              <Calendar size={13} className="text-slate-500" />
              <span className="font-medium">{selectedDate || "Select Date"}</span>
              <ChevronDown size={12} className={`text-slate-500 transition-transform ${isCalOpen ? 'rotate-180' : ''}`} />
            </button>

            {isCalOpen && (
              <div className="absolute top-full right-0 mt-2 w-72 bg-slate-800 border border-slate-700/60 rounded-lg shadow-2xl shadow-black/40 z-50 p-5 font-sans text-slate-200">
                <div className="flex items-center justify-between mb-4">
                  <div className="font-semibold text-sm">{calendarData.month} <span className="text-slate-500 ml-1 font-mono">{calendarData.year}</span></div>
                  <div className="flex gap-1">
                    <button onClick={() => { const d = new Date(selectedDate); d.setMonth(d.getMonth() - 1); setSelectedDate(d.toISOString().split('T')[0]); }} className="p-1 hover:bg-slate-700/50 rounded"><ChevronLeft size={14} /></button>
                    <button onClick={() => { const d = new Date(selectedDate); d.setMonth(d.getMonth() + 1); setSelectedDate(d.toISOString().split('T')[0]); }} className="p-1 hover:bg-slate-700/50 rounded"><ChevronRight size={14} /></button>
                  </div>
                </div>
                <div className="grid grid-cols-7 mb-2 text-center text-[10px] font-mono text-slate-500">
                  {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(d => <div key={d} className="py-1">{d}</div>)}
                </div>
                <div className="grid grid-cols-7 gap-0.5 text-[12px] font-mono">
                  {Array.from({ length: calendarData.firstDayOfMonth }).map((_, i) => <div key={`e-${i}`} />)}
                  {Array.from({ length: calendarData.daysInMonth }).map((_, i) => {
                    const day = i + 1;
                    const dStr = `${calendarData.year}-${(new Date(selectedDate).getMonth() + 1).toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
                    const isAvail = dates.includes(dStr);
                    const isSel = selectedDate === dStr;
                    return (
                      <button key={day} onClick={() => { if (isAvail) { setSelectedDate(dStr); setIsCalOpen(false); } }}
                        className={`py-1.5 rounded text-center transition-all ${isSel ? 'bg-blue-600 text-white font-bold' : isAvail ? 'hover:bg-slate-700/50 text-slate-300' : 'opacity-15 cursor-not-allowed'}`}
                      >{day}</button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <button onClick={handleExport} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 border border-slate-700/60 hover:border-slate-500/50 rounded-md text-[11px] font-mono uppercase transition-all text-slate-400 hover:text-slate-200">
            <Download size={13} className="text-slate-500" /> Export
          </button>
        </div>
      </header>

      {/* ─── FILTER BAR ─── */}
      <div className="bg-slate-900 border-b border-slate-800 px-5 py-2.5 shrink-0 overflow-x-auto">
        <div className="flex items-center gap-5 min-w-max">
          {/* Search */}
          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700/60 rounded-md px-3 py-1.5 focus-within:border-blue-500/50 transition-all w-44">
            <Search size={13} className="text-slate-500 shrink-0" />
            <input
              placeholder="Search symbol..."
              className="bg-transparent border-none outline-none text-slate-200 font-mono text-[11px] placeholder:text-slate-600 uppercase w-full"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
            {searchTerm && <button onClick={() => setSearchTerm('')} className="text-slate-500 hover:text-slate-300"><X size={12} /></button>}
          </div>

          <div className="h-5 w-px bg-[#1c2030]" />

          <div className="flex items-center gap-2">
            <FilterInput label="Score" value={exactScore} onChange={setExactScore} placeholder="5" type="number" width="w-16" />
            {exactScore && !isNaN(Number(exactScore)) && (
              <span className="bg-slate-800 text-blue-400 font-mono text-xs px-2 py-1 rounded-md border border-slate-700/60 shadow-sm ml-1">
                ({scoreCounts[Number(exactScore)] || 0})
              </span>
            )}
          </div>

          <div className="h-5 w-px bg-[#1c2030]" />

          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">Dist %</span>
            <input type="number" className="bg-slate-800 border border-slate-700/60 rounded-md focus:border-blue-500/60 outline-none px-2.5 py-1.5 w-14 text-slate-200 font-mono text-[11px] text-center placeholder:text-slate-600 transition-all" placeholder="Min" value={minDist} onChange={e => setMinDist(e.target.value)} />
            <span className="text-slate-600 text-[10px]">to</span>
            <input type="number" className="bg-slate-800 border border-slate-700/60 rounded-md focus:border-blue-500/60 outline-none px-2.5 py-1.5 w-14 text-slate-200 font-mono text-[11px] text-center placeholder:text-slate-600 transition-all" placeholder="Max" value={maxDist} onChange={e => setMaxDist(e.target.value)} />
          </div>

          <div className="h-5 w-px bg-[#1c2030]" />

          <FilterSelect label="RSI" value={rsiZone} onChange={setRsiZone} options={[
            { value: "All", label: "ALL ZONES" }, { value: "Healthy", label: "HEALTHY (40–60)" },
            { value: "Oversold", label: "OVERSOLD (<40)" }, { value: "Overbought", label: "OVERBOUGHT (>60)" }
          ]} />

          <div className="h-5 w-px bg-[#1c2030]" />

          <FilterSelect label="Trend" value={trend} onChange={setTrend} options={[
            { value: "All", label: "ALL" }, { value: "Bullish", label: "▲ BULLISH" }, { value: "Bearish", label: "▼ BEARISH" }
          ]} />

          <div className="h-5 w-px bg-[#1c2030]" />

          <FilterSelect label="Mkt Cap" value={marketCap} onChange={setMarketCap} options={[
            { value: "All", label: "ANY" }, { value: "Large", label: "LARGE" },
            { value: "Mid", label: "MID" }, { value: "Small", label: "SMALL" }, { value: "Micro", label: "MICRO" }
          ]} />

          <div className="h-5 w-px bg-[#1c2030]" />

          <FilterInput label="Tags" value={tagsInput} onChange={setTagsInput} placeholder="N50, PHARMA" type="text" width="w-28" />

          {hasActiveFilters && (
            <>
              <div className="h-5 w-px bg-[#1c2030]" />
              <button onClick={resetFilters} className="flex items-center gap-1.5 text-[10px] font-semibold uppercase text-slate-500 hover:text-terminal-red tracking-wider transition-colors">
                <RotateCcw size={11} /> Reset
              </button>
            </>
          )}
        </div>
      </div>

      {/* ─── TABLE ─── */}
      <div className="flex-1 overflow-auto bg-slate-950 relative">
        <table className="w-full text-left border-collapse min-w-[1200px]">
          <thead className="bg-slate-900 sticky top-0 z-20">
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id} className="border-b-2 border-slate-800">
                {hg.headers.map(header => (
                  <th
                    key={header.id}
                    className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest cursor-pointer hover:text-slate-300 hover:bg-slate-800/50 transition-colors select-none group"
                    onClick={header.column.getToggleSortingHandler()}
                    style={{ width: header.getSize() }}
                  >
                    <div className="flex items-center gap-1.5" style={{ justifyContent: ['LTP', 'Score', 'RSI_14', 'Weighted_Avg', 'Dist_Weighted_Avg_PCT'].includes(header.column.id) ? 'flex-end' : header.column.id === 'link' ? 'center' : 'flex-start' }}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        <span className={`transition-opacity ${header.column.getIsSorted() ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`}>
                          {{ asc: <ChevronDown className="w-3.5 h-3.5 text-terminal-green rotate-180" />, desc: <ChevronDown className="w-3.5 h-3.5 text-terminal-red" /> }[header.column.getIsSorted() as string] ?? <ChevronDown className="w-3.5 h-3.5" />}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row, i) => (
              <tr key={row.id} className={`border-b border-slate-800/60 hover:bg-slate-800 transition-colors ${i % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/40'}`}>
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-6 py-5 align-middle">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {table.getRowModel().rows.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-slate-600">
            <Search size={36} className="opacity-15" />
            <div className="text-xs font-mono uppercase tracking-[0.15em]">No Signals Match Current Filters</div>
            {hasActiveFilters && (
              <button onClick={resetFilters} className="text-[11px] text-blue-400 hover:text-blue-300 font-mono uppercase tracking-wider transition-colors">Reset All Filters</button>
            )}
          </div>
        )}
      </div>

      {/* ─── FOOTER ─── */}
      <div className="h-7 bg-slate-900 border-t border-slate-800 flex items-center justify-between px-5 text-[10px] font-mono text-slate-600 uppercase tracking-[0.12em] shrink-0">
        <span>SwingLogic Quantitative Terminal v2.4</span>
        <div className="flex items-center gap-4">
          <span>{filteredData.length} <span className="text-slate-500">signals</span></span>
          <span>{allUniqueTags.length} <span className="text-slate-500">tags indexed</span></span>
        </div>
      </div>
    </div>
  );
}