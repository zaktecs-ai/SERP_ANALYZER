# Fiverr SERP Analyzer

A production-ready Fiverr keyword/SERP research tool for web-scraping-related
keywords. Collects and analyzes the top 20 visible Fiverr gigs for each keyword
from public, logged-out search results, and produces advanced keyword
opportunity / competition analysis.

## ⚡ Quick Start — 2-Click Setup

The project uses a **virtual environment** (`.venv`) to keep all libraries
isolated from your system Python. No conflicts with anything else on your
computer.

### Windows

| Step | What to do | When |
|------|-----------|------|
| 1 | Double-click **`setup.bat`** | First time only |
| 2 | Double-click **`run.bat`** | Every time after |

**`setup.bat`** creates the isolated `.venv` folder and installs all
dependencies. Takes ~30 seconds, one-time only.

**`run.bat`** automatically activates the environment, checks dependencies,
and launches the analyzer. Also creates the `.venv` automatically if you
skipped step 1.

### Linux / macOS

```bash
chmod +x setup.sh run.sh

./setup.sh    # First time only (creates .venv, installs deps)
./run.sh      # Every time after
```

### Manual (any OS)

```bash
cd fiverr_serp_analyzer

# Create isolated environment (first time)
python -m venv .venv

# Activate it
.venv\Scripts\activate     # Windows (Command Prompt)
.venv\Scripts\Activate.ps1 # Windows (PowerShell)
source .venv/bin/activate   # Linux / macOS

# Install dependencies (first time)
pip install -r requirements.txt

# Run
python main.py --input keywords.csv
```

### What's the virtual environment for?

| | Without venv (old) | With venv (new) |
|---|---|---|
| Libraries installed in | System-wide Python folder | Project's `.venv/` folder only |
| Conflicts with other projects | Yes — version clashes possible | Zero — completely isolated |
| Uninstall / cleanup | Messy, affects other projects | Just delete the `.venv/` folder |
| Works on any PC without admin | Sometimes needs admin rights | Always works, no admin needed |


## Usage

```bash
# Process keywords from CSV (default: keywords.csv)
python main.py --input keywords.csv

# Collect top 25 gigs per keyword
python main.py --input keywords.csv --top 25

# Retry previously failed keywords
python main.py --input keywords.csv --resume

# Reprocess everything, ignoring checkpoints
python main.py --input keywords.csv --force

# Analyze a single keyword
python main.py --keyword "scrape ecommerce website"

# Limit keywords per run
python main.py --input keywords.csv --max-keywords 25
```

### Live Progress Output

```
[12/100] scrape ecommerce website
  Collecting SERP... found 20 gigs
  Analyzing competitors...
  Opportunity Score: 82.4
  Saved.
```

## Constraints (Non-Negotiable)

1. **Headed Browser Only (C1)**: The browser MUST run headed (visible). Headless
   is prohibited. The app refuses to start if `browser.headless: true`.
2. **No Proxy (C2)**: All traffic goes direct from your machine. No proxy,
   VPN, or IP rotation.
3. **Attended Operation (C3)**: This tool runs while you watch it. Any security
   challenge is handled by YOU manually (see Challenge Handling).
4. **No Security-Control Circumvention (C4)**: No CAPTCHA solving, fingerprint
   spoofing, stealth patches, or account automation.
5. **Conservative Pacing (C5)**: Low request frequency, randomized delays,
   one keyword at a time, no parallel sessions.
6. **Accuracy Over Completeness (C6)**: Missing data is `null`, never `0`.
   Missing reviews ≠ 0 reviews. Missing price ≠ $0.

## Challenge Handling (Attended Mode)

On detecting a CAPTCHA, "verify you are human" interstitial, or block page,
the tool:

1. Pauses all automation immediately.
2. Alerts via terminal bell + prominent console banner.
3. Keeps the browser window open and untouched for you to solve manually.
4. Waits for ENTER (indefinitely by default).
5. Re-verifies the page before resuming.
6. Logs the event to `logs/collection.log`.

If challenges exceed `max_challenges_per_run` (default 3), the run ends
gracefully with all progress saved. Never attempts automated solving.

## Configuration (config.yaml)

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| browser | headless | false | Locked — app refuses to start if true |
| browser | page_timeout | 30 | Page load timeout (seconds) |
| collection | top_n | 20 | Number of top gigs per keyword |
| collection | delay_min | 3 | Min delay between actions (sec) |
| collection | delay_max | 7 | Max delay between actions (sec) |
| collection | keyword_pause_min | 8 | Min pause between keywords (sec) |
| collection | keyword_pause_max | 15 | Max pause between keywords (sec) |
| collection | max_retries | 2 | Technical failure retries |
| collection | max_keywords_per_run | 0 | Max keywords (0 = unlimited) |
| collection | max_challenges_per_run | 3 | Max challenges before graceful stop |
| interaction | natural_scroll | true | Progressive lazy-load scrolling |
| interaction | mouse_movement | true | Gentle cursor movements |
| interaction | idle_probability | 0.2 | Random idle pause probability |
| analysis | demand_weight | 0.25 | Opportunity score demand weight |
| analysis | intent_weight | 0.20 | Opportunity score intent weight |
| analysis | relevance_weight | 0.20 | Opportunity score relevance weight |
| analysis | competition_weight | 0.25 | Opportunity score competition weight |
| analysis | serp_weakness_weight | 0.10 | Opportunity score SERP weakness weight |

## Scoring Methodology

### Opportunity Score Formula

```
Opportunity = Demand*0.25 + Intent*0.20 + Relevance*0.20
            + (100-Competition)*0.25 + (100-SERP_Strength)*0.10
```

### Component Definitions

#### Demand Score (0-100)
Based on Fiverr's visible total result count. **This is NOT search volume.**
It's the number of gigs Fiverr returns for the keyword — a rough demand signal.

| Total Results | Score | Signal |
|---------------|-------|--------|
| < 100 | 10 | very_low |
| < 500 | 25 | low |
| < 2,000 | 50 | moderate |
| < 10,000 | 75 | high |
| >= 10,000 | 100 | very_high |
| Unknown | 50 | unknown |

#### Intent Score (0-100)
Rule-based NLP classification of buyer intent:

| Intent | Score Weight |
|--------|-------------|
| transactional | 40 |
| service_specific | 35 |
| commercial | 15 |
| niche_service | 10 |
| informational | 0 |

Higher intent = more likely to convert to a purchase.

#### Relevance Score (0-100)
How closely the top-20 gig titles match the keyword:

```
Relevance = (ExactTitleMatch% * 40) + (PartialTitleMatch% * 30)
          + (AvgTokenMatchRatio * 30)
```

#### Competition Score (0-100)
Multi-signal competition analysis — never result count alone:

- Median review count of top 20
- Median rating
- Review distribution (quartiles/percentiles)
- Seller level distribution
- Established seller concentration
- Top-5 vs bottom-15 review strength

#### SERP Strength Score (0-100)
Concentration of reviews among top sellers:

- Top-5 review share of total
- Top-10 review share of total
- Median review count
- 75th/90th percentile review counts

Higher SERP Strength = established sellers dominate = harder to break in.

## Data Quality

Every extracted field carries a state:

| State | Meaning |
|-------|---------|
| extracted | Successfully parsed from the page |
| missing | Field not present on the page |
| inferred | Derived from other data (rare, always flagged) |
| parsing_failed | Element found but value unparseable |

Raw strings are stored alongside every parsed value (e.g. raw `"1.2k"` plus
parsed `1200`). All values are labeled:
`observed | calculated | assumption | inferred opportunity`.

## Output Files

| File | Description |
|------|-------------|
| `fiverr_serp_analysis.xlsx` | Full Excel report (9 sheets with filters, formatting) |
| `keyword_summary.csv` | Per-keyword summary and scores |
| `top20_gigs.csv` | All collected gig data |
| `competitor_analysis.csv` | Per-gig competitor scores |
| `keyword_opportunities.csv` | Keywords ranked by opportunity |
| `results.json` | Full structured raw data |
| `data/fiverr_serp.db` | SQLite database (keywords, gigs, sellers, runs, errors) |
| `logs/collection.log` | Collection event log |
| `logs/errors.log` | Error log |
| `screenshots/` | Screenshots on parsing failures |
| `data/html_failures/` | HTML snapshots on parsing failures |
| `data/checkpoint.json` | Resume/checkpoint data |

## Architecture

```
fiverr_serp_analyzer/
├── main.py              # CLI entry point
├── requirements.txt
├── config.yaml
├── keywords.csv
├── scraper/
│   ├── browser.py       # Headed Chrome management
│   ├── fiverr.py        # SERP collection orchestration
│   ├── selectors.py     # ALL selectors centralized here
│   ├── parsers.py       # Field extraction with fallbacks
│   ├── challenge.py     # Challenge detection + attended mode
│   └── interaction.py   # Human-paced interaction behaviors
├── analysis/
│   ├── keywords.py      # Intent, relevance, demand
│   ├── competition.py   # Multi-signal competition analysis
│   ├── scoring.py       # Opportunity score engine
│   ├── clustering.py    # Keyword clustering
│   └── gap_analysis.py  # Opportunity gap identification
├── database/
│   ├── models.py        # SQLite schema
│   └── storage.py       # Storage layer with upserts
├── reports/
│   ├── excel.py         # Excel report generator
│   ├── csv_export.py    # CSV exporters
│   └── json_export.py   # JSON exporter
├── utils/
│   ├── logging.py       # Collection + error logging
│   ├── normalization.py # Text/number/URL normalization
│   └── checkpoint.py    # Resume capability
├── data/                # SQLite DB + HTML failures
├── logs/
├── screenshots/
└── tests/               # Unit + fixture-based tests
```

## Testing

```bash
cd fiverr_serp_analyzer
python -m unittest discover tests
```

## Security

- No hard-coded credentials. Environment variables only if credentials are
  genuinely required (the tool works on public SERP data without an account).
- Never logs passwords, cookies, session tokens, or credentials.
- No CAPTCHA solving, no stealth patches, no evasion techniques.
- Natural human-paced interaction for session stability in an attended,
  supervised session. These behaviors are NOT stealth or anti-detection tools.

## Fiverr-Specific Assumptions

1. **Selectors may change**: All selectors are centralized in
   `scraper/selectors.py`. If Fiverr's HTML changes, update a selector there.
2. **Lazy loading**: Fiverr loads gig cards progressively. The tool scrolls
   naturally to trigger rendering. If fewer than top_n cards render, the
   actual count is recorded — never padded.
3. **Total results**: Fiverr's displayed result count is stored raw AND
   parsed. It is treated as a demand signal, NOT exact competition or search
   volume.
4. **Public data only**: The tool collects publicly visible search results.
   No login, no private data.
5. **Challenges are possible**: Fiverr may present security challenges.
   The tool handles this via attended mode — you solve it manually.
