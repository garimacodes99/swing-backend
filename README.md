# Swing Trading Intelligence Engine

A modular stock analysis and swing trading dashboard built using Python and React.

This project automates:

- Market data fetching
- Swing analysis computation
- JSON generation
- Frontend data syncing
- Historical snapshot indexing

---

# Features

## Backend

- Yahoo Finance OHLCV data fetching
- Modular swing analysis engine
- RSI-based analysis
- Weighted average distance analysis
- Automated JSON generation
- Automated frontend sync
- Historical snapshot indexing

## Frontend

- React + Vite dashboard
- Daily swing snapshot visualization
- Filter/search functionality
- Google Finance integration
- Historical data browsing

---

# Project Structure

```bash
swing_trading_engine/
│
├── fetchers/                 # Market data fetchers
├── logic/                    # Core swing analysis logic
├── runners/                  # Pipeline runners
├── utils/                    # Utility modules
├── universe/                 # Stock universe CSV
├── output/                   # Backend generated outputs
│
├── frontend/
│   ├── public/data/close/    # Frontend JSON snapshots
│   └── src/                  # React frontend
│
└── README.md
```

---

# Tech Stack

## Backend

- Python
- Pandas
- yFinance

## Frontend

- React
- Vite

---

# Automated Pipeline

The analysis pipeline works as follows:

```text
Run Analysis Script
        ↓
Fetch Market Data
        ↓
Compute Swing Logic
        ↓
Generate JSON Snapshot
        ↓
Copy Snapshot To Frontend
        ↓
Update index.json
        ↓
Frontend Ready
```

---

# Running The Project

## 1. Clone Repository

```bash
git clone <your-repository-url>
cd swing_trading_engine
```

---

## 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

## 4. Run Close Analysis

From project root:

```bash
python runners/run_close_analysis.py
```

This will:

- generate JSON snapshot
- sync frontend data
- update index.json automatically

---

## 5. Start Frontend

```bash
cd frontend
npm run dev
```

---

# Output Format

Generated snapshots are stored in:

```text
frontend/public/data/close/
```

Example:

```text
swing_close_2026-05-22.json
```

---

# Current Analysis Metrics

- RSI 14
- Weighted Average
- Distance Percentage
- LTP Tracking

---

# Future Improvements

- SMA 50 / SMA 200 integration
- ATR analysis
- Swing scoring system
- Sector-level analysis
- Historical performance tracking
- Auto deployment pipeline
- Cloud database integration

---

# Disclaimer

This project is for educational and research purposes only.

This is not financial advice.
