import os

app_path = r"c:\Users\YUVAL\OneDrive\Desktop\swing_trading_engine\frontend\src\App.tsx"

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# FilterInput replacement
old_filter_input = """const FilterInput = ({ label, value, onChange, placeholder, type = "text", width = "w-16" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string; width?: string;
}) => (
  <div className="flex items-center gap-2">
    <span className="text-[10px] uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">{label}</span>
    <input
      type={type}
      className={`bg-[#141820] border border-[#252a38] rounded-md focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/20 outline-none px-2.5 py-1.5 ${width} text-slate-200 font-mono text-[11px] text-center placeholder:text-slate-600 transition-all`}"""

new_filter_input = """const FilterInput = ({ label, value, onChange, placeholder, type = "text", width = "w-16" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string; width?: string;
}) => (
  <div className="flex items-center gap-2.5">
    <span className="text-xs uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">{label}</span>
    <input
      type={type}
      className={`bg-slate-800 border border-slate-700/60 rounded-md hover:border-slate-500 focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/20 outline-none px-3 py-2 ${width} text-slate-200 font-mono text-sm text-center placeholder:text-slate-500 transition-all shadow-sm`}"""

content = content.replace(old_filter_input, new_filter_input)

# FilterSelect replacement
old_filter_select = """const FilterSelect = ({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[];
}) => (
  <div className="flex items-center gap-2">
    <span className="text-[10px] uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">{label}</span>
    <select
      className={`bg-[#141820] border rounded-md outline-none px-2.5 py-1.5 text-[11px] cursor-pointer font-mono transition-all ${
        value !== 'All' ? 'border-blue-500/50 text-blue-300 bg-blue-500/5' : 'border-[#252a38] text-slate-300'
      } focus:border-blue-500/60`}"""

new_filter_select = """const FilterSelect = ({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[];
}) => (
  <div className="flex items-center gap-2.5">
    <span className="text-xs uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">{label}</span>
    <select
      className={`bg-slate-800 border rounded-md outline-none px-3 py-2 text-sm cursor-pointer font-mono transition-all hover:border-slate-500 shadow-sm ${
        value !== 'All' ? 'border-blue-500/50 text-blue-300 bg-blue-500/5' : 'border-slate-700/60 text-slate-300'
      } focus:border-blue-500/60`}"""

content = content.replace(old_filter_select, new_filter_select)

# State renaming
content = content.replace('const [minScore, setMinScore] = useState("");', 'const [exactScore, setExactScore] = useState("");')
content = content.replace('const hasActiveFilters = searchTerm || minScore ||', 'const hasActiveFilters = searchTerm || exactScore ||')
content = content.replace('setSearchTerm(""); setMinScore(""); setMinDist(""); setMaxDist("");', 'setSearchTerm(""); setExactScore(""); setMinDist(""); setMaxDist("");')

# Filter logic replacement
old_filter_logic = """  // ── Filtered Data ──
  const filteredData = useMemo(() => {
    let data = [...rows].filter(r => r.date === selectedDate);

    // Merge score + tags into each row
    data = data.map(r => {
      const meta = scoreMap[(r.Ticker || '').toUpperCase()];
      return { ...r, Score: meta?.score, Tags: meta?.tags || '', TagList: meta?.tagList || [] };
    });

    // Search
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      data = data.filter(r => r.Ticker?.toLowerCase().includes(q));
    }

    // Score ≥
    if (minScore !== "") {
      const n = Number(minScore);
      if (!isNaN(n)) data = data.filter(r => (r.Score ?? -Infinity) >= n);
    }"""

new_filter_logic = """  // ── Filtered Data & Score Counts ──
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
    }"""

content = content.replace(old_filter_logic, new_filter_logic)

# useMemo deps update
content = content.replace('] = useMemo(() => {', ' } = useMemo(() => {')
content = content.replace(
  '  }, [rows, selectedDate, searchTerm, minScore, minDist, maxDist, rsiZone, marketCap, trend, tagsInput, scoreMap]);',
  '    return { filteredData: data, scoreCounts: counts };\n  }, [rows, selectedDate, searchTerm, exactScore, minDist, maxDist, rsiZone, marketCap, trend, tagsInput, scoreMap]);'
)

# Render replacements
content = content.replace('bg-[#0a0d12]', 'bg-slate-950')
content = content.replace('bg-[#0d1017]', 'bg-slate-900')
content = content.replace('bg-[#090c10]', 'bg-slate-950')
content = content.replace('border-[#1c2030]', 'border-slate-800')
content = content.replace('border-[#151a24]', 'border-slate-800/60')
content = content.replace('bg-[#141820]', 'bg-slate-800')
content = content.replace('border-[#252a38]', 'border-slate-700/60')
content = content.replace('bg-[#0c1018]', 'bg-slate-900/40')

old_search = """          {/* Search */}
          <div className="flex items-center gap-2 bg-[#141820] border border-[#252a38] rounded-md px-3 py-1.5 focus-within:border-blue-500/50 transition-all w-44">
            <Search size={13} className="text-slate-500 shrink-0" />
            <input
              placeholder="Search symbol..."
              className="bg-transparent border-none outline-none text-slate-200 font-mono text-[11px] placeholder:text-slate-600 uppercase w-full"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
            {searchTerm && <button onClick={() => setSearchTerm('')} className="text-slate-500 hover:text-slate-300"><X size={12} /></button>}
          </div>"""

new_search = """          {/* Search */}
          <div className="flex items-center gap-2.5 bg-slate-800 border border-slate-700/60 rounded-md px-3 py-2 hover:border-slate-500 focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/20 transition-all w-52 shadow-sm">
            <Search size={14} className="text-slate-500 shrink-0" />
            <input
              placeholder="Search symbol..."
              className="bg-transparent border-none outline-none text-slate-200 font-mono text-sm placeholder:text-slate-500 uppercase w-full"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
            {searchTerm && <button onClick={() => setSearchTerm('')} className="text-slate-500 hover:text-slate-300"><X size={14} /></button>}
          </div>"""

content = content.replace(old_search, new_search)

old_score_comp = """          <FilterInput label="Score ≥" value={minScore} onChange={setMinScore} placeholder="0" type="number" width="w-14" />"""
new_score_comp = """          <div className="flex items-center gap-2">
            <FilterInput label="Score" value={exactScore} onChange={setExactScore} placeholder="5" type="number" width="w-16" />
            {exactScore && !isNaN(Number(exactScore)) && (
              <span className="bg-slate-800 text-blue-400 font-mono text-xs px-2 py-1 rounded-md border border-slate-700/60 shadow-sm ml-1">
                ({scoreCounts[Number(exactScore)] || 0})
              </span>
            )}
          </div>"""
content = content.replace(old_score_comp, new_score_comp)

old_dist = """          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">Dist %</span>
            <input type="number" className="bg-[#141820] border border-[#252a38] rounded-md focus:border-blue-500/60 outline-none px-2.5 py-1.5 w-14 text-slate-200 font-mono text-[11px] text-center placeholder:text-slate-600 transition-all" placeholder="Min" value={minDist} onChange={e => setMinDist(e.target.value)} />
            <span className="text-slate-600 text-[10px]">to</span>
            <input type="number" className="bg-[#141820] border border-[#252a38] rounded-md focus:border-blue-500/60 outline-none px-2.5 py-1.5 w-14 text-slate-200 font-mono text-[11px] text-center placeholder:text-slate-600 transition-all" placeholder="Max" value={maxDist} onChange={e => setMaxDist(e.target.value)} />
          </div>"""

new_dist = """          <div className="flex items-center gap-2.5">
            <span className="text-xs uppercase text-slate-500 font-semibold tracking-wider whitespace-nowrap">Dist %</span>
            <input type="number" className="bg-slate-800 border border-slate-700/60 rounded-md hover:border-slate-500 focus:border-blue-500/60 outline-none px-3 py-2 w-16 text-slate-200 font-mono text-sm text-center placeholder:text-slate-500 transition-all shadow-sm" placeholder="Min" value={minDist} onChange={e => setMinDist(e.target.value)} />
            <span className="text-slate-500 text-xs">to</span>
            <input type="number" className="bg-slate-800 border border-slate-700/60 rounded-md hover:border-slate-500 focus:border-blue-500/60 outline-none px-3 py-2 w-16 text-slate-200 font-mono text-sm text-center placeholder:text-slate-500 transition-all shadow-sm" placeholder="Max" value={maxDist} onChange={e => setMaxDist(e.target.value)} />
          </div>"""
content = content.replace(old_dist, new_dist)


# Table styles adjustments
content = content.replace('px-5 py-3', 'px-6 py-4')
content = content.replace('text-[11px] font-bold text-slate-500 uppercase tracking-[0.08em]', 'text-xs font-bold text-slate-500 uppercase tracking-widest')
content = content.replace('text-left border-collapse min-w-[1100px]', 'text-left border-collapse min-w-[1200px]')
content = content.replace('text-[13px]', 'text-[14px]')
content = content.replace('hover:bg-[#141820]/50 transition-colors', 'hover:bg-slate-800/40 transition-colors')

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done with replacements.")
