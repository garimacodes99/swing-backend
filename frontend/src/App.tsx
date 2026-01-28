import { useEffect, useMemo, useState, useRef } from "react";
import { useSnapshotStore } from "./store/snapshotStore";
import { 
  Calendar, Search, Download, ChevronDown, 
  Activity, TrendingUp, Layers, 
  X, Filter, ArrowUpDown,
  ShieldCheck, Zap, Globe, BarChart3, Info, Settings2,
  ChevronLeft, ChevronRight,
  ExternalLink, Gauge, LineChart, PieChart
} from "lucide-react";

/* --- ENHANCED UI PRIMITIVES --- */
const Badge = ({ label, type }: { label: string; type: 'success' | 'danger' | 'info' | 'neutral' | 'warning' }) => {
  const styles = {
    success: 'bg-gradient-to-r from-emerald-50 to-emerald-100 text-emerald-700 border-emerald-400 shadow-emerald-100',
    danger: 'bg-gradient-to-r from-rose-50 to-rose-100 text-rose-700 border-rose-400 shadow-rose-100',
    info: 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-700 border-blue-400 shadow-blue-100',
    warning: 'bg-gradient-to-r from-amber-50 to-amber-100 text-amber-700 border-amber-400 shadow-amber-100',
    neutral: 'bg-gradient-to-r from-slate-50 to-slate-100 text-slate-700 border-slate-400 shadow-slate-100',
  };
  return (
    <span className={`px-2.5 py-1 rounded-md text-[9px] font-bold uppercase tracking-tight border shadow-sm ${styles[type]} transition-all hover:scale-105`}>
      {label || 'N/A'}
    </span>
  );
};

const GroupHeader = ({ label, icon: Icon, color }: any) => (
  <div className="flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-700">
    <Icon size={16} strokeWidth={3} className={`${color} drop-shadow-sm`} />
    <span className="text-[10px] font-black text-white uppercase tracking-widest drop-shadow-sm" style={{ fontFamily: 'Inter, system-ui, sans-serif', letterSpacing: '0.1em' }}>{label}</span>
  </div>
);

export default function SwingTerminalLight() {
  const { rows, load } = useSnapshotStore();
  
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'Swing_Score', direction: 'desc' });
  
  const [minConviction, setMinConviction] = useState(48);
  const [onlyBuy, setOnlyBuy] = useState(true);
  const [minSwingScore, setMinSwingScore] = useState(0);
  const [maxSwingScore, setMaxSwingScore] = useState(100);
  const [showFilters, setShowFilters] = useState(false);
  
  const [isCalOpen, setIsCalOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const calRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    load();
    fetch("/data/index.json").then(r => r.json()).then(i => {
      const dList = i.dates.map((d: any) => d.date).reverse();
      setDates(dList);
      if (dList.length > 0) setSelectedDate(dList[0]);
    }).catch(err => console.error("Error loading index:", err));
  }, [load]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (calRef.current && !calRef.current.contains(event.target as Node)) {
        setIsCalOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const calendarData = useMemo(() => {
    if (!selectedDate) return { month: '', year: '', daysInMonth: 0, firstDayOfMonth: 0 };
    const date = new Date(selectedDate);
    const month = date.toLocaleString('default', { month: 'long' });
    const year = date.getFullYear();
    const firstDayOfMonth = new Date(date.getFullYear(), date.getMonth(), 1).getDay();
    const daysInMonth = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    
    return { month, year, firstDayOfMonth, daysInMonth };
  }, [selectedDate]);

  const handleMonthChange = (offset: number) => {
    const current = new Date(selectedDate);
    current.setMonth(current.getMonth() + offset);
    const newDateStr = current.toISOString().split('T')[0];
    setSelectedDate(newDateStr);
  };

  const filteredData = useMemo(() => {
    let data = [...rows].filter(r => r.date === selectedDate);
    if (searchTerm) data = data.filter(r => r.Ticker?.toLowerCase().includes(searchTerm.toLowerCase()));
    if (onlyBuy) data = data.filter(r => r.Swing_Label === 'BUY');
    
    data = data.filter(r => {
      const score = r.Swing_Score || 0;
      return score >= minSwingScore && score <= maxSwingScore;
    });
    
    data = data.filter(r => (r.Swing_Score || 0) >= minConviction);
    
    data.sort((a, b) => {
      const aVal = (a as any)[sortConfig.key] ?? (sortConfig.direction === 'asc' ? Infinity : -Infinity);
      const bVal = (b as any)[sortConfig.key] ?? (sortConfig.direction === 'asc' ? Infinity : -Infinity);
      if (aVal === bVal) return 0;
      const result = aVal > bVal ? 1 : -1;
      return sortConfig.direction === 'asc' ? result : -result;
    });
    return data;
  }, [rows, selectedDate, searchTerm, minConviction, onlyBuy, minSwingScore, maxSwingScore, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig(prev => ({ 
      key, 
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc' 
    }));
  };

  const kpis = useMemo(() => ({
    signals: filteredData.length,
    avgScore: filteredData.length ? (filteredData.reduce((acc, r) => acc + (r.Swing_Score || 0), 0) / filteredData.length).toFixed(1) : 0,
    breadth: filteredData.length ? ((filteredData.filter(r => (r.Return_3M_PCT || 0) > 0).length / filteredData.length) * 100).toFixed(0) : 0
  }), [filteredData]);

  const handleExport = () => {
    const headers = [
      'S.No', 'Ticker', 'LTP', 'RSI_14', 'RSI_Zone', 'ATR_PCT', 
      'Volatility_Class', 'SMA_200', 'Dist_SMA200_PCT', 'Trend_Regime',
      'Return_3M_PCT', 'Return_6M_PCT', 'Return_1Y_PCT', 'High_52W', 
      'Low_52W', 'Swing_Score', 'Swing_Label'
    ];
    
    const csvContent = [
      headers.join(','),
      ...filteredData.map((r, i) => [
        i + 1, r.Ticker, r.LTP, r.RSI_14, r.RSI_Zone, r.ATR_PCT, 
        r.Volatility_Class, r.SMA_200, r.Dist_SMA200_PCT, r.Trend_Regime,
        r.Return_3M_PCT, r.Return_6M_PCT, r.Return_1Y_PCT, r.High_52W,
        r.Low_52W, r.Swing_Score, r.Swing_Label
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `swing-signals-${selectedDate}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 text-slate-900 flex flex-col overflow-hidden" style={{ fontFamily: 'Inter, system-ui, -apple-system, sans-serif' }}>
      
      <div className="flex flex-1 overflow-hidden">
        {/* ENHANCED SIDEBAR */}
        <aside className={`${sidebarOpen ? 'w-80' : 'w-0'} bg-white/95 backdrop-blur-xl border-r border-slate-200 transition-all duration-300 flex flex-col z-40 overflow-hidden shadow-2xl shadow-slate-200/50`}>
          <div className="p-6 border-b border-slate-200 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600 rounded-lg shadow-lg shadow-blue-200">
                <Settings2 size={16} strokeWidth={3} className="text-white" />
              </div>
              <div>
                <span className="text-[12px] font-black text-slate-900 uppercase tracking-wide block">Strategy Panel</span>
                <span className="text-[9px] font-medium text-slate-500">Advanced Filters</span>
              </div>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 p-1.5 rounded-lg transition-all">
              <X size={18} />
            </button>
          </div>

          <div className="p-6 space-y-8 flex-1 overflow-y-auto">
            {/* Conviction Floor Section */}
            <section className="space-y-4 p-5 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl border border-blue-200 shadow-md">
              <div className="flex justify-between items-center">
                <label className="text-[10px] font-black text-slate-700 uppercase tracking-widest flex items-center gap-2">
                  <div className="p-1.5 bg-blue-600 rounded-md">
                    <ShieldCheck size={11} strokeWidth={3} className="text-white" />
                  </div>
                  Conviction Floor
                </label>
                <div className="px-3 py-1.5 bg-blue-600 rounded-lg shadow-lg shadow-blue-200">
                  <span className="text-sm font-black text-white">{minConviction}%</span>
                </div>
              </div>
              <div className="relative">
                <input
                  type="range" min="0" max="100" value={minConviction}
                  onChange={(e) => setMinConviction(parseInt(e.target.value))}
                  className="w-full accent-blue-600 h-2 bg-gradient-to-r from-slate-200 to-blue-100 rounded-full cursor-pointer appearance-none"
                  style={{
                    background: `linear-gradient(to right, rgb(37, 99, 235) 0%, rgb(37, 99, 235) ${minConviction}%, rgb(226, 232, 240) ${minConviction}%, rgb(226, 232, 240) 100%)`
                  }}
                />
                <div className="flex justify-between mt-2">
                  <span className="text-[8px] font-bold text-slate-500">0%</span>
                  <span className="text-[8px] font-bold text-slate-500">100%</span>
                </div>
              </div>

              <button
                onClick={() => setOnlyBuy(!onlyBuy)}
                className={`w-full py-3 rounded-xl border-2 text-[11px] font-black uppercase transition-all flex items-center justify-center gap-2.5 shadow-md ${
                  onlyBuy 
                    ? 'bg-gradient-to-r from-emerald-500 to-emerald-600 border-emerald-600 text-white shadow-emerald-200' 
                    : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Zap size={14} strokeWidth={3} className={onlyBuy ? 'animate-pulse' : ''} /> 
                {onlyBuy ? 'Buy Signals Only ✓' : 'Show All Signals'}
              </button>
            </section>

            {/* Swing Score Range Section */}
            <section className="space-y-4 p-5 bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl border border-slate-200 shadow-md">
              <label className="text-[10px] font-black text-slate-700 uppercase tracking-widest flex items-center gap-2">
                <div className="p-1.5 bg-slate-700 rounded-md">
                  <Gauge size={11} strokeWidth={3} className="text-white" />
                </div>
                Swing Score Range
              </label>
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-black text-slate-500 uppercase">Minimum</span>
                    <span className="text-xs font-black text-slate-700 bg-white px-2 py-0.5 rounded-md border border-slate-300">{minSwingScore}</span>
                  </div>
                  <input 
                    type="range" min="0" max="100" value={minSwingScore} 
                    onChange={(e) => setMinSwingScore(Math.min(parseInt(e.target.value), maxSwingScore))} 
                    className="w-full accent-slate-600 h-1.5 bg-slate-200 rounded-full cursor-pointer" 
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-black text-slate-500 uppercase">Maximum</span>
                    <span className="text-xs font-black text-slate-700 bg-white px-2 py-0.5 rounded-md border border-slate-300">{maxSwingScore}</span>
                  </div>
                  <input 
                    type="range" min="0" max="100" value={maxSwingScore} 
                    onChange={(e) => setMaxSwingScore(Math.max(parseInt(e.target.value), minSwingScore))} 
                    className="w-full accent-slate-600 h-1.5 bg-slate-200 rounded-full cursor-pointer" 
                  />
                </div>
              </div>
            </section>
          </div>
        </aside>

        {/* MAIN CONTENT AREA */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* ENHANCED HEADER */}
          <header className="h-20 bg-white/95 backdrop-blur-xl border-b border-slate-200 flex items-center justify-between px-8 z-30 shadow-lg shadow-slate-100">
            <div className="flex items-center gap-6">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="p-2.5 rounded-xl transition-all bg-blue-600 text-white shadow-lg shadow-blue-200 hover:shadow-xl hover:scale-105"
                >
                  <Filter size={18} strokeWidth={3} />
                </button>
              )}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
                  <LineChart size={20} strokeWidth={3} className="text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-black text-slate-900 tracking-tight">
                    SWING<span className="text-blue-600">LOGIC</span>
                  </h1>
                  <p className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Professional Trading Terminal</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Calendar */}
              <div className="relative" ref={calRef}>
                <button
                  onClick={() => setIsCalOpen(!isCalOpen)}
                  className={`flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-slate-50 to-slate-100 border-2 rounded-xl transition-all shadow-md hover:shadow-lg ${
                    isCalOpen ? 'border-blue-500 shadow-blue-100' : 'border-slate-300'
                  }`}
                >
                  <Calendar size={16} strokeWidth={3} className="text-blue-600" />
                  <div className="flex flex-col items-start">
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Selected Date</span>
                    <span className="text-[11px] font-black text-slate-900">{selectedDate || "Pick Date"}</span>
                  </div>
                  <ChevronDown size={16} className={`text-slate-400 transition-transform ${isCalOpen ? 'rotate-180' : ''}`} />
                </button>

                {isCalOpen && (
                  <div className="absolute top-full right-0 mt-3 w-80 bg-white border-2 border-slate-900 rounded-2xl shadow-2xl z-50 p-6 animate-in fade-in zoom-in-95 duration-200">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex flex-col">
                        <span className="text-[15px] font-black text-slate-900 leading-none">{calendarData.month}</span>
                        <span className="text-[11px] font-bold text-blue-600 mt-0.5">{calendarData.year}</span>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => handleMonthChange(-1)} className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-all"><ChevronLeft size={16} /></button>
                        <button onClick={() => handleMonthChange(1)} className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-all"><ChevronRight size={16} /></button>
                      </div>
                    </div>

                    <div className="flex gap-2 mb-4">
                      <button 
                        onClick={() => {
                          const today = new Date().toISOString().split('T')[0];
                          if (dates.includes(today)) setSelectedDate(today);
                        }}
                        className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-black text-[10px] font-black uppercase rounded-lg transition-all"
                      >
                        Today
                      </button>
                      <button 
                        onClick={() => {
                          const yest = new Date();
                          yest.setDate(yest.getDate() - 1);
                          const yestStr = yest.toISOString().split('T')[0];
                          if (dates.includes(yestStr)) setSelectedDate(yestStr);
                        }}
                        className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-black text-[10px] font-black uppercase rounded-lg transition-all"
                      >
                        Yesterday
                      </button>
                    </div>

                    <div className="grid grid-cols-7 mb-3 text-center">
                      {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => (
                        <div key={d} className="text-[10px] font-black text-slate-400 uppercase tracking-tight py-2">{d}</div>
                      ))}
                    </div>
                    <div className="grid grid-cols-7 gap-1">
                      {Array.from({ length: calendarData.firstDayOfMonth }).map((_, i) => (
                        <div key={`empty-${i}`} className="aspect-square" />
                      ))}
                      {Array.from({ length: calendarData.daysInMonth }).map((_, i) => {
                        const day = i + 1;
                        const dateObj = new Date(selectedDate);
                        const dateStr = `${dateObj.getFullYear()}-${(dateObj.getMonth() + 1).toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
                        const isAvailable = dates.includes(dateStr);
                        const isSelected = selectedDate === dateStr;
                        return (
                          <button
                            key={day}
                            onClick={() => { if(isAvailable) { setSelectedDate(dateStr); setIsCalOpen(false); } }}
                            className={`aspect-square flex flex-col items-center justify-center rounded-xl text-[12px] font-bold transition-all relative ${
                              isSelected 
                                ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-200 scale-110 z-10' 
                                : 'text-black hover:bg-blue-50 hover:text-blue-700 hover:scale-105'
                            } ${!isAvailable ? 'opacity-20 cursor-not-allowed' : ''}`}
                          >
                            {day}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              <button 
                onClick={handleExport} 
                className="bg-gradient-to-r from-slate-800 to-slate-900 hover:from-slate-900 hover:to-black text-white px-5 py-3 rounded-xl text-[11px] font-black uppercase flex items-center gap-2.5 transition-all shadow-lg shadow-slate-300 hover:shadow-xl hover:scale-105"
              >
                <Download size={14} strokeWidth={3} /> Export CSV
              </button>
            </div>
          </header>
          
          <div className="p-8 space-y-6 overflow-y-auto flex-1">
            {/* KPI CARDS */}
            <div className="grid grid-cols-4 gap-5">
              {[
                { label: 'Active Signals', val: kpis.signals, icon: Zap, color: 'blue' },
                { label: 'Avg Conviction', val: `${kpis.avgScore}%`, icon: Gauge, color: 'emerald' },
                { label: 'Market Breadth', val: `${kpis.breadth}%`, icon: PieChart, color: 'indigo' },
                { label: 'Score Floor', val: `${minConviction}%`, icon: ShieldCheck, color: 'rose' }
              ].map((stat, i) => (
                <div key={i} className={`bg-${stat.color}-280 border-2 border-white p-6 rounded-2xl shadow-lg hover:shadow-xl transition-all cursor-default hover:scale-95 group`}>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <span className="text-[10px] font-black text-slate-600 uppercase tracking-wider block mb-1">{stat.label}</span>
                      <div className={`text-3xl font-black text-${stat.color}-600 tracking-tight`}>{stat.val}</div>
                    </div>
                    <div className={`bg-${stat.color}-600 p-3 rounded-xl shadow-lg group-hover:scale-110 transition-transform`}>
                      <stat.icon size={20} strokeWidth={3} className="text-white" />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* SEARCH & FILTERS */}
            <div className="bg-white/95 backdrop-blur-xl border-2 border-slate-200 rounded-2xl p-6 shadow-lg space-y-5">
              <div className="flex items-center gap-4">
                <div className="flex-1 flex items-center gap-3 bg-gradient-to-r from-slate-50 to-slate-100 border-2 border-slate-200 rounded-xl px-5 py-3.5 transition-all focus-within:border-blue-500 focus-within:shadow-lg focus-within:shadow-blue-100">
                  <Search size={18} strokeWidth={3} className="text-slate-400" />
                  <input 
                    placeholder="Search by ticker symbol..." 
                    className="bg-transparent border-none outline-none text-[13px] font-semibold text-slate-800 w-full placeholder:text-slate-400" 
                    value={searchTerm} 
                    onChange={(e) => setSearchTerm(e.target.value)} 
                  />
                  {searchTerm && (
                    <button onClick={() => setSearchTerm('')} className="text-slate-600 hover:text-slate-900 transition-colors">
                      <X size={16} />
                    </button>
                  )}
                </div>
                <button 
                  onClick={() => setShowFilters(!showFilters)} 
                  className={`flex items-center gap-2.5 px-5 py-3.5 rounded-xl border-2 text-[11px] font-black uppercase transition-all shadow-md ${
                    showFilters 
                      ? 'bg-gradient-to-r from-blue-600 to-blue-600 border-blue-500 text-white shadow-blue-400' 
                      : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Settings2 size={15} strokeWidth={3} /> Advanced Filters 
                  <ChevronDown size={15} className={`transition-transform ${showFilters ? 'rotate-180' : ''}`} />
                </button>
              </div>

              {showFilters && (
                <div className="grid grid-cols-2 gap-6 pt-5 border-t-2 border-slate-100 animate-in fade-in slide-in-from-top-2">
                  <div className="space-y-3">
                    <label className="text-[10px] font-black text-slate-600 uppercase tracking-widest flex items-center gap-2">
                      <Activity size={12} strokeWidth={3} className="text-blue-600" /> RSI Zone Filter
                    </label>
                    <select className="w-full bg-gradient-to-r from-slate-50 to-slate-100 border-2 border-slate-200 rounded-xl p-3 text-[12px] font-bold text-slate-700 outline-none focus:border-blue-500 transition-all cursor-pointer">
                      <option>All Zones</option>
                      <option>Healthy</option>
                      <option>Oversold</option>
                      <option>Overbought</option>
                    </select>
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-black text-slate-600 uppercase tracking-widest flex items-center gap-2">
                      <TrendingUp size={12} strokeWidth={3} className="text-emerald-600" /> Volatility Class
                    </label>
                    <select className="w-full bg-gradient-to-r from-slate-50 to-slate-100 border-2 border-slate-200 rounded-xl p-3 text-[12px] font-bold text-slate-700 outline-none focus:border-blue-500 transition-all cursor-pointer">
                      <option>All Volatility</option>
                      <option>Low Vol</option>
                      <option>Medium Vol</option>
                      <option>High Vol</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* ENHANCED TABLE */}
            <div className="bg-white/95 backdrop-blur-xl border-2 border-slate-300 rounded-2xl overflow-hidden shadow-2xl shadow-slate-200">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[2300px] table-fixed">
                  <thead>
                    <tr className="border-b-2 border-slate-700">
                      <th className="w-16 border-r-2 border-slate-700 sticky left-0 z-20 bg-gradient-to-r from-slate-800 to-slate-700">
                        <div className="px-4 py-3 text-[10px] font-black text-white uppercase tracking-widest text-center"></div>
                      </th>
                      <th className="w-48 border-r-2 border-slate-700 sticky left-16 z-20">
                        <GroupHeader label="Core Assets" icon={Layers} color="text-blue-400" />
                      </th>
                      <th colSpan={1} className="border-r-2 border-slate-700"><GroupHeader label="Price Info" icon={Info} color="text-slate-300" /></th>
                      <th colSpan={2} className="border-r-2 border-slate-700"><GroupHeader label="Momentum" icon={Zap} color="text-blue-400" /></th>
                      <th colSpan={2} className="border-r-2 border-slate-700"><GroupHeader label="Volatility" icon={Activity} color="text-rose-400" /></th>
                      <th colSpan={3} className="border-r-2 border-slate-700"><GroupHeader label="Trend Regime" icon={TrendingUp} color="text-emerald-400" /></th>
                      <th colSpan={3} className="border-r-2 border-slate-700"><GroupHeader label="Returns" icon={BarChart3} color="text-indigo-400" /></th>
                      <th colSpan={2} className="border-r-2 border-slate-700"><GroupHeader label="52W Range" icon={Globe} color="text-blue-300" /></th>
                      <th colSpan={2} className="border-r-2 border-slate-700"><GroupHeader label="Verdict" icon={ShieldCheck} color="text-blue-400" /></th>
                      <th className="sticky right-0 bg-slate-800 z-20"><GroupHeader label="Link" icon={ExternalLink} color="text-slate-300" /></th>
                    </tr>
                    <tr className="bg-gradient-to-r from-slate-100 to-slate-50 border-b-2 border-slate-300 text-[13px] font-black text-slate-900 uppercase tracking-wider">
                      <th className="p-4 w-16 text-center border-r-2 border-slate-200 sticky left-0 z-20 bg-slate-100">S.No</th>
                      <th className="p-4 border-r-2 border-slate-200 sticky left-16 z-20 bg-slate-100">Ticker</th>
                      {[
                        { l: 'LTP', k: 'LTP' },
                        { l: 'RSI 14', k: 'RSI_14' }, { l: 'RSI Zone', k: 'RSI_Zone' }, 
                        { l: 'ATR %', k: 'ATR_PCT' }, { l: 'Vol Class', k: 'Volatility_Class' }, 
                        { l: 'SMA 200', k: 'SMA_200' }, { l: 'Dist %', k: 'Dist_SMA200_PCT' }, { l: 'Regime', k: 'Trend_Regime' }, 
                        { l: '3M %', k: 'Return_3M_PCT' }, { l: '6M %', k: 'Return_6M_PCT' }, { l: '1Y %', k: 'Return_1Y_PCT' }, 
                        { l: '52W High', k: 'High_52W' }, { l: '52W Low', k: 'Low_52W' },
                        { l: 'Score', k: 'Swing_Score' }, { l: 'Label', k: 'Swing_Label' }
                      ].map((col, idx) => (
                        <th 
                          key={idx} 
                          onClick={() => handleSort(col.k)} 
                          className={`p-4 cursor-pointer hover:bg-slate-200 transition-all group border-r-2 border-slate-200 ${sortConfig.key === col.k ? 'bg-blue-100' : ''}`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            {col.l} 
                            <ArrowUpDown size={11} strokeWidth={3} className={`transition-all ${sortConfig.key === col.k ? 'opacity-100 text-blue-700 scale-110' : 'opacity-30 group-hover:opacity-100'}`} />
                          </div>
                        </th>
                      ))}
                      <th className="p-4 text-center border-l-2 border-slate-200 sticky right-0 bg-slate-100 z-20">
                        <ExternalLink size={17} strokeWidth={3} className="mx-auto text-slate-500" />
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {filteredData.map((r, i) => (
                      <tr key={`${r.Ticker}-${i}`} className="hover:bg-gradient-to-r hover:from-blue-50/50 hover:to-indigo-50/30 transition-all duration-200 group border-b border-slate-100">
                        <td className="p-4 text-center font-bold text-[12px] text-slate-600 border-r-2 border-slate-200 bg-slate-50/80 sticky left-0 z-10 group-hover:bg-blue-100/50 transition-colors">{i + 1}</td>
                        <td 
                          className="p-4 font-black text-[12px] text-slate-700 border-r-2 border-slate-200 uppercase sticky left-16 z-10 bg-white group-hover:bg-gradient-to-r group-hover:from-blue-50 group-hover:to-indigo-50 group-hover:text-blue-700 transition-all"
                          style={{ fontFamily: 'Arial, sans-serif' }}
                        >
                          {r.Ticker}
                        </td>
                        <td className="p-4 font-bold text-[12px] text-slate-700 border-r-2 border-slate-200">₹{r.LTP?.toLocaleString()}</td>
                        <td className="p-4 font-black text-[12px] text-slate-700 border-r-2 border-slate-200">{r.RSI_14?.toFixed(1)}</td>
                        <td className="p-4 border-r-2 border-slate-200">
                          <Badge label={r.RSI_Zone} type={r.RSI_Zone === 'Oversold' ? 'success' : r.RSI_Zone === 'Overbought' ? 'danger' : 'info'} />
                        </td>
                        <td className="p-4 font-bold text-[12px] text-slate-500 border-r-2 border-slate-200">{r.ATR_PCT?.toFixed(2)}%</td>
                        <td className="p-4 border-r-2 border-slate-200"><Badge label={r.Volatility_Class} type="neutral" /></td>
                        <td className="p-4 font-bold text-[12px] text-slate-700 border-r-2 border-slate-200">₹{r.SMA_200?.toLocaleString()}</td>
                        <td className={`p-4 font-black text-[12px] border-r-2 border-slate-200 ${(r.Dist_SMA200_PCT || 0) > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                          {r.Dist_SMA200_PCT?.toFixed(2)}%
                        </td>
                        <td className="p-4 border-r-2 border-slate-200">
                          <Badge label={r.Trend_Regime} type={(r.Trend_Regime || '').includes('BULLISH') ? 'success' : 'danger'} />
                        </td>
                        <td className="p-4 font-bold text-[12px] text-slate-700 border-r-2 border-slate-200">{r.Return_3M_PCT?.toFixed(1)}%</td>
                        <td className="p-4 font-bold text-[12px] text-slate-700 border-r-2 border-slate-200">{r.Return_6M_PCT?.toFixed(1)}%</td>
                        <td className="p-4 font-bold text-[12px] text-slate-700 border-r-2 border-slate-200">{r.Return_1Y_PCT?.toFixed(1)}%</td>
                        <td className="p-4 font-bold text-[12px] text-blue-600 border-r-2 border-slate-200">₹{r.High_52W?.toLocaleString()}</td>
                        <td className="p-4 font-bold text-[12px] text-rose-500 border-r-2 border-slate-200">₹{r.Low_52W?.toLocaleString()}</td>
                        <td className="p-4 border-r-2 border-slate-200">
                          <div className="flex items-center gap-3">
                            <span className="text-[12px] font-black text-slate-700 w-8">{r.Swing_Score}</span>
                            <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden shadow-inner border border-slate-200">
                              <div 
                                className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full shadow-[0_0_8px_rgba(37,99,235,0.4)]" 
                                style={{ width: `${r.Swing_Score}%` }} 
                              />
                            </div>
                          </div>
                        </td>
                        <td className="p-4 border-r-2 border-slate-200">
                          <Badge label={r.Swing_Label} type={r.Swing_Label === 'BUY' ? 'success' : 'danger'} />
                        </td>
                        <td className="p-4 text-center border-l-2 border-slate-200 sticky right-0 bg-white group-hover:bg-slate-50 z-10 transition-colors">
                          <a 
                            href={`https://www.google.com/finance/quote/${r.Ticker}:NSE`} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center p-2 rounded-lg bg-slate-100 text-slate-600 hover:bg-blue-600 hover:text-white transition-all shadow-sm"
                          >
                            <ExternalLink size={14} strokeWidth={3} />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}