#!/usr/bin/env python3
"""
RowAnalysis — World Rowing Race Data Fetcher & Parser

Downloads race data PDFs from World Rowing, parses speed & stroke rate
per 50m, and outputs JSON for the web visualizer.

Usage:
  python3 fetch_race.py <event_code> <boat_class> <round> <race_num>
  python3 fetch_race.py --list <event_code>
  python3 fetch_race.py --events

Examples:
  python3 fetch_race.py ECH_2026_1 M1x FA 100
  python3 fetch_race.py --list ECH_2026_1
  python3 fetch_race.py --events
"""

import sys
import re
import json
import os
import subprocess
import tempfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ── Event Code Map ──────────────────────────────────────────
# Format: {event_slug: (event_code, event_name)}
EVENT_CODES = {
    "2026-ECH":     ("ECH_2026_1",     "2026 European Rowing Championships"),
    "2026-WCH":     ("WCH_2026_1",     "2026 World Rowing Championships"),
    "2025-WCH":     ("WCH_2025_1",     "2025 World Rowing Championships"),
    "2026-WC1":     ("WCp1_2026_1",    "2026 World Rowing Cup I"),
    "2026-WC2":     ("WCp2_2026_1",    "2026 World Rowing Cup II"),
    "2026-WC3":     ("WCp3_2026_1",    "2026 World Rowing Cup III"),
    "2025-WC1":     ("WCp1_2025_1",    "2025 World Rowing Cup I"),
    "2025-WC2":     ("WCp2_2025_1",    "2025 World Rowing Cup II"),
    "2025-WC3":     ("WCp3_2025_1",    "2025 World Rowing Cup III"),
}

# Boat class codes for the PDF filename
BOAT_CLASSES = {
    "M1x": "ROWMSCULL1", "W1x": "ROWWSCULL1",
    "M2-": "ROWMPAIR2",  "W2-": "ROWWPAIR2",
    "M2x": "ROWMDSCULL2","W2x": "ROWWDSCULL2",
    "M4-": "ROWMFOUR4",  "W4-": "ROW WFOUR4",
    "M4x": "ROW MQUAD4", "W4x": "ROW WQUAD4",
    "M8+": "ROWMEIGHT8", "W8+": "ROWWEIGHT8",
    "LM2x":"ROWLMDSCULL2","LW2x":"ROWLWDSCULL2",
    "LM1x":"ROWLMS CULL1","LW1x":"ROWLWSCULL1",
    "LM2-":"ROWLMPAIR2", "LW2-":"ROWLWPAIR2",
}

ROUND_CODES = {"FA": "FNL", "FB": "FNL", "FC": "FNL", "FD": "FNL",
               "SF": "SEM", "HEAT": "HEA", "QUARTER": "QUA",
               "PRELIM": "PRE"}

CLOUDFRONT = "https://d3fpn4c9813ycf.cloudfront.net/pdfDocuments"


def get_pdf_url(event_code, boat_class, round_code, race_num):
    """Build the World Rowing race data PDF URL."""
    # Try different filename patterns
    patterns = [
        f"{event_code}/{event_code}_{boat_class}------------{round_code}-{race_num:06d}--_C77X1632.PDF",
        f"{event_code}/{event_code}_{boat_class}------------{round_code}-000100--_C77X1632.PDF",
        f"{event_code}/{event_code}_{boat_class}------------{round_code}-{race_num:06d}--_C77X1632.PDF",
        # The race_num in the PDF filename doesn't always match the actual race number
        # Try common race numbers
        # Try common race numbers
        f"{event_code}/{event_code}_{boat_class}------------{round_code}-000100--_C77X1632.PDF",
        f"{event_code}/{event_code}_{boat_class}------------{round_code}-000001--_C77X1632.PDF",
        f"{event_code}/{event_code}_{boat_class}------------{round_code}-000200--_C77X1632.PDF",
    ]
    return [f"{CLOUDFRONT}/{p}" for p in patterns]


def download_pdf(url, timeout=30):
    """Download a PDF from a URL using curl (more reliable SSL handling)."""
    import subprocess
    import tempfile
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            outpath = f.name
    except Exception:
        return None
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", outpath, "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=timeout
        )
        status = result.stdout.strip()
        if status == "200":
            with open(outpath, "rb") as f:
                data = f.read()
            os.unlink(outpath)
            return data
        os.unlink(outpath)
        return None
    except Exception as e:
        try:
            os.unlink(outpath)
        except:
            pass
        return None


def extract_text_from_pdf(pdf_data):
    """Extract text from PDF data using pdftotext or fallback."""
    # Try pdftotext
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_data)
            pdf_path = f.name
        result = subprocess.run(
            ["pdftotext", pdf_path, "-"],
            capture_output=True, text=True, timeout=15
        )
        os.unlink(pdf_path)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Fallback: extract text from PDF raw content
    text = ""
    i = 0
    in_paren = False
    current = ""
    while i < len(pdf_data):
        b = pdf_data[i]
        if b == 0x28:  # (
            in_paren = True
            current = ""
        elif b == 0x29:  # )
            in_paren = False
            if current.strip():
                text += current + "\n"
        elif in_paren:
            if 0x20 <= b < 0x7f:
                current += chr(b)
            elif b == 0x5c:  # escape
                if i + 1 < len(pdf_data):
                    n = pdf_data[i + 1]
                    if n == 0x6e:  # \n
                        current += "\n"
                        i += 1
                    elif n == 0x72:  # \r
                        current += "\r"
                        i += 1
                    elif n == 0x28:  # \(
                        current += "("
                        i += 1
                    elif n == 0x29:  # \)
                        current += ")"
                        i += 1
        i += 1
    return text


def parse_race_data(text):
    """Parse race data text into structured JSON.
    
    Format: column-major — each column (distance, speed1, rate1, speed2, rate2, ...)
    is listed vertically, one value per line.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None

    # Extract metadata
    venue = lines[0] if len(lines) > 0 else "Unknown"
    
    # Find date
    date = ""
    for l in lines[:10]:
        m = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', l)
        if m:
            date = m.group(1)
            break
    
    # Find boat class
    boat_class = "Unknown"
    for l in lines[:10]:
        if re.match(r'^[MWL][1-8][x+:\-]?$', l):
            boat_class = l
            break
    
    # Find round
    round_code = "Unknown"
    for l in lines[:10]:
        if re.match(r'^(FA|FB|FC|FD|SF\d?|HEAT|QUARTER|PRELIM)', l, re.IGNORECASE):
            round_code = l.upper()
            break
    
    # Find race number
    race_num = ""
    for l in lines[:10]:
        m = re.search(r'Race\s+(\d+)', l)
        if m:
            race_num = m.group(1)
            break
    
    # Find country codes (after "Country" line, before "Rank")
    countries = []
    country_found = False
    for l in lines:
        if l == "Country":
            country_found = True
            continue
        if country_found:
            if re.match(r'^[A-Z]{3}\d?$', l):
                countries.append(l)
            elif l == "Rank":
                break
    
    # Find ranks (after "Rank" line)
    ranks = []
    rank_found = False
    for l in lines:
        if l == "Rank":
            rank_found = True
            continue
        if rank_found:
            try:
                r = int(l)
                ranks.append(r)
            except ValueError:
                break
    
    # Find where data begins (after the last header column)
    # Count Speed/Stroke pairs to know number of columns
    num_boats = len(countries)
    if num_boats == 0:
        num_boats = len(ranks)
    if num_boats == 0:
        return None
    
    # Find the data start: after "Dist." line and the column headers
    # Each boat has: Speed, [m/s], Stroke, (spm) = 4 lines
    # Plus: Dist., [m] = 2 lines
    header_count = 2 + 4 * num_boats  # Dist + [m] + (Speed/m/s/Stroke/spm) * num_boats
    
    # Find Dist. line
    dist_idx = -1
    for i, l in enumerate(lines[:50]):
        if l == "Dist.":
            # Check if next line is [m]
            if i + 1 < len(lines) and lines[i + 1] == "[m]":
                dist_idx = i
                break
    
    if dist_idx < 0:
        return None
    
    data_start = dist_idx + header_count
    
    # Now read columns: each column has data until the next column header or end
    # The columns are: Dist, (Speed, Rate) × num_boats
    num_cols = 1 + 2 * num_boats
    
    # Read all numerical values from data_start onward
    values = []
    for l in lines[data_start:]:
        try:
            v = float(l)
            values.append(v)
        except ValueError:
            # Skip non-numeric lines (like "Page 2/2", etc.)
            if l.startswith("INTERNET") or l.startswith("Page") or l.startswith("Report"):
                break
    
    # Each column should have 40 values (50m to 2000m)
    if len(values) < num_cols * 10:  # At least 10 data points per column
        return None
    
    # Split into columns
    col_len = len(values) // num_cols
    cols = [values[i * col_len:(i + 1) * col_len] for i in range(num_cols)]
    
    distances = cols[0]
    
    # Build boats
    boats = []
    for b in range(num_boats):
        speed_idx = 1 + b * 2
        rate_idx = 2 + b * 2
        
        if speed_idx < len(cols) and rate_idx < len(cols):
            speed = cols[speed_idx]
            rate = cols[rate_idx]
            
            if len(speed) > 10:
                boats.append({
                    "country": countries[b] if b < len(countries) else f"LANE{b+1}",
                    "rank": ranks[b] if b < len(ranks) else b + 1,
                    "lane": b + 1,
                    "speed": speed,
                    "rate": rate
                })
    
    return {
        "venue": venue,
        "date": date,
        "event": "World Rowing Race Data",
        "class": boat_class,
        "round": round_code,
        "raceNum": race_num,
        "boats": boats
    }


def list_events():
    """List available events."""
    print("Available Events:")
    print("=" * 60)
    for slug, (code, name) in sorted(EVENT_CODES.items()):
        print(f"  {slug:20s} → {code:20s}  {name}")
    print()
    print("Usage: python3 fetch_race.py <event_slug> <boat_class> <round> <race_num>")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("RowAnalysis — World Rowing Race Data Fetcher")
        print()
        print("Usage:")
        print("  python3 fetch_race.py <event_slug> <boat_class> <round> <race_num>")
        print("  python3 fetch_race.py --events")
        print("  python3 fetch_race.py --list <event_slug>")
        print()
        print("Example:")
        print("  python3 fetch_race.py 2025-WCH W1x FA 135")
        print("  python3 fetch_race.py --events")
        return
    
    if sys.argv[1] == "--events":
        list_events()
        return
    
    if len(sys.argv) < 5:
        print("Usage: python3 fetch_race.py <event_slug> <boat_class> <round> <race_num>")
        sys.exit(1)
    
    event_slug = sys.argv[1]
    boat_class = sys.argv[2]
    round_str = sys.argv[3]
    race_num = int(sys.argv[4])
    
    if event_slug not in EVENT_CODES:
        print(f"Unknown event: {event_slug}")
        print("Use --events to list available events")
        sys.exit(1)
    
    if boat_class not in BOAT_CLASSES:
        print(f"Unknown boat class: {boat_class}")
        sys.exit(1)
    
    event_code = EVENT_CODES[event_slug][0]
    event_name = EVENT_CODES[event_slug][1]
    class_code = BOAT_CLASSES[boat_class]
    round_code = ROUND_CODES.get(round_str, round_str)
    
    # Get PDF URLs
    urls = get_pdf_url(event_code, class_code, round_code, race_num)
    
    print(f"Fetching: {event_name}")
    print(f"  Class: {boat_class} ({class_code})")
    print(f"  Round: {round_str} → {round_code}")
    print(f"  Race:  #{race_num}")
    print()
    
    pdf_data = None
    used_url = None
    for url in urls:
        print(f"  Trying: {url.split('/')[-1][:80]}...")
        pdf_data = download_pdf(url)
        if pdf_data:
            used_url = url
            print(f"  ✓ Downloaded ({len(pdf_data)//1024} KB)")
            break
        else:
            print(f"  ✗ Not found")
    
    if not pdf_data:
        print("  ✗ Could not find this race data PDF")
        print("  The race may not have tracking data, or the filename pattern is different.")
        return
    
    # Parse
    text = extract_text_from_pdf(pdf_data)
    if not text.strip():
        print("  ✗ Could not extract text from PDF")
        return
    
    race_data = parse_race_data(text)
    if not race_data or not race_data.get("boats"):
        print("  ✗ Could not parse race data from PDF")
        print("  Raw text preview:")
        for l in text.split("\n")[:30]:
            print(f"    {l.strip()}")
        return
    
    # Output
    print(f"\n  Parsed {len(race_data['boats'])} boats:")
    for b in race_data["boats"]:
        avg_speed = sum(b["speed"]) / len(b["speed"])
        avg_rate = sum(b["rate"]) / len(b["rate"]) if b["rate"] else 0
        print(f"    #{b['rank']} {b['country']} (Lane {b['lane']}): {avg_speed:.2f} m/s, {avg_rate:.0f} spm, {len(b['speed'])} segments")
    
    # Save JSON
    output = {"source": used_url, **race_data}
    
    # Also output as JSON for the web tool
    outfile = f"race_{event_code}_{boat_class}_{round_str}_{race_num}.json"
    with open(outfile, "w") as f:
        json.dump(race_data, f, indent=2)
    print(f"\n  ✓ Saved to {outfile}")
    
    # Embedded JS data format
    print("\n  JS snippet for web visualizer:")
    js_data = json.dumps(race_data)
    print(f"    const raceData = {js_data};")


if __name__ == "__main__":
    main()