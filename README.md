# RowAnalysis 🚣

**Race data visualizer for World Rowing competitions.**  
Speed, stroke rate, and pacing analysis from World Rowing race data PDFs.

Built for the **2026 European Rowing Championships** (Varese, Italy) — works with any World Rowing race that has tracking data.

## Live Demo

Open `index.html` in a browser. No server needed.

## What It Does

| Feature | Description |
|---------|-------------|
| **Speed Over Distance** | Line chart showing each boat's speed (m/s) at every 50m |
| **Stroke Rate Over Distance** | Line chart showing stroke rate (spm) through the race |
| **Pacing Profile** | Speed vs stroke rate scatter plot — see how each boat combines rate and power |
| **500m Split Times** | Bar chart comparing each 500m segment |
| **Speed Differential** | How each boat compares to the winner at every 50m |
| **Race Insights** | Auto-generated analysis: pacing, rate changes, sprint finish, gaps |

## Data Source

World Rowing publishes detailed race data for every major championship:

- **Speed** (m/s) every 50m
- **Stroke rate** (spm) every 50m  
- Per boat, per race

The data is available as PDFs from the World Rowing CDN and through the **World Rowing Data Platform** at [raceanalysis.worldrowing.com](https://raceanalysis.worldrowing.com/).

## Using the Web Tool

### Option 1: Load Example Data
Click any of the example cards (W1x, M8+, M2x) to see sample data from the 2025 World Champs.

### Option 2: Upload a PDF
Drag and drop a World Rowing race data PDF onto the upload zone.

### Option 3: Fetch from World Rowing (Python)
```bash
# List available events
python3 fetch_race.py --events

# Fetch a specific race
python3 fetch_race.py 2025-WCH W1x FA 135

# Output is saved as race_*.json — load it into the web tool
```

## Data Format

World Rowing race data PDFs contain:
- Venue, date, event info
- Boat class and round (FA, FB, SF, HEAT)
- Country codes and finishing ranks
- 40 data points (50m to 2000m) per boat:
  - **Speed** in m/s (e.g., 5.3 = ~19.1 km/h)
  - **Stroke rate** in strokes per minute

## Understanding the Charts

### Speed (m/s)
- **Start (0-50m)**: Highest speed — boats accelerate from standing start
- **Middle (500-1500m)**: Settled race pace — lowest speed, most efficient
- **Finish (1500-2000m)**: Sprint — speed increases again

### Stroke Rate (spm)
- **Start**: 44-48 spm for quick acceleration
- **Middle**: 34-38 spm for endurance cruising
- **Finish**: 38-42 spm for sprint

### Pacing Profiles
- **Even pacing**: Consistent speed throughout (most efficient)
- **Fly-and-die**: Fast start, significant slowdown
- **Strong finish**: Negative split — faster in the second half
- **Positive split**: Faster first half, slower second half

## Event Codes

| Code | Event |
|------|-------|
| `2026-ECH` | 2026 European Rowing Championships (Varese) |
| `2025-WCH` | 2025 World Rowing Championships (Shanghai) |
| `2026-WC1` | 2026 World Rowing Cup I (Seville) |
| `2026-WC2` | 2026 World Rowing Cup II (Plovdiv) |
| `2026-WC3` | 2026 World Rowing Cup III (Lucerne) |

## Project Structure

```
rowanalysis/
├── index.html          # Web visualizer (standalone, no server needed)
├── fetch_race.py       # Python CLI tool to download & parse PDFs
└── README.md           # This file
```

## Technical Notes

- **No API key needed** — World Rowing data is publicly available
- **No server required** — the web tool is a single HTML file
- **Chart.js** for interactive charts
- **PDF parsing** via pdftotext (install poppler) or built-in fallback
- The World Rowing Data Platform at raceanalysis.worldrowing.com has its own interactive tools but no public JSON API

## License

Data source: World Rowing (worldrowing.com).  
This tool is for analysis and visualization purposes.