
---

## 🧾 README

### Overview

This Python project allows you to scrape both the **match history** and the **upcoming matches** of a **team** or a **competition** from [oddsPortal.com](https://www.oddsportal.com).

It provides detailed information for a given **sport**, **team**, or **competition** during a specific **season**, according to user-defined parameters.

---

### 📊 Collected Data

#### For a competition

In addition to the general information provided by the user (`season`, `bookmaker`, `market`, `region`, `competition`, `sport`), the script collects for each match:

* Match score
* Home team
* Away team
* Opening and closing odds (value, date, and time) for outcome **1**, **X**, and **2** in the **1X2** market

Depending on the `typegame` and `spread` options, the scraper adapts its behavior:

| Key          | Description                                                      | Possible Values                                                                                                                                         | Default        |
| ------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| **typegame** | Defines whether to scrape **upcoming** or **historical** matches | `"upcoming"` or `"historical"`                                                                                                                          | `"historical"` |
| **spread**   | Defines the scraping scope for competitions                      | `"none"` (only the selected competition) / `"team"` (also fetches team histories) / `"completly"` (fetches all teams + all competitions they played in) | `"none"`       |

For example:

* `typegame="historical"`, `spread="team"` → fetches the competition’s match history + all participating teams’ histories.
* `typegame="upcoming"` → fetches only **upcoming matches** of the competition.

When `spread` is `"team"` or `"completly"`, already-scraped data in `scraped_data/` are **skipped** to avoid redundancy and save time.

#### For a team

The script collects the same information as for competitions, plus:

* The **region** where the competition takes place
* The **competition name**

⚠️ The odds are retrieved according to the specified bookmaker.

---

### ⚙️ Requirements

* **Python 3.x**
* **Playwright**

---

### 💻 Installation

```bash
git clone https://github.com/djibril-marega/oddsportal_scraper.git
cd oddsportal_scraper
pip install -r requirements.txt
```

---

### 🚀 Usage

#### Method 1 — Recommended (modular and reproducible)

Create a `.json` configuration file containing teams or competitions.

Example for a **team**:

```json
[
  {
    "sport": "Football",
    "region": "France",
    "team": "PSG",
    "teamid": "CjhkPw0k",
    "season": "2024/2025",
    "bookmaker": "Betclic"
  }
]
```

Example for a **competition** (historical data):

```json
[
  {
    "sport": "Football",
    "region": "England",
    "competition": "Premier League",
    "season": "2024/2025",
    "bookmaker": "Betclic"
  }
]
```

Example for **upcoming matches** of a competition:

```json
[
  {
    "sport": "Football",
    "region": "France",
    "competition": "Ligue 1",
    "season": "2025/2026",
    "bookmaker": "Betclic",
    "typegame": "upcoming"
  }
]
```

To execute the script:

```bash
python .\run_parallel_tests.py
```

* Logs are stored in the `logs/` directory — one file per team/competition, plus a global summary log.
* Scraped data are saved in `scraped_data/` — one file per team/competition.
* To enable verbose output:

  ```bash
  python .\run_parallel_tests.py -v
  ```

---

#### Method 2 — Quick test (less reproducible)

Run directly with `pytest`:

```bash
pytest test_oddsportal.py --sport=Football --region=France --competition="Ligue 1" --season=2025/2026 --bookmaker=Betclic --typegame=upcoming -v --tb=short
```

Options:

* `--typegame`: `"upcoming"` or `"historical"`
* `--spread`: `"none"`, `"team"`, or `"completly"`
* `-v`: verbose mode
* `--tb=short`: concise traceback

---

## 📁 Output Structure

```
project/
│
├── scraped_data/        # One file per team or competition
├── logs/                # Detailed and summary logs
├── run_parallel_tests.py
└── test_oddsportal.py
```

---

## 🧠 Notes

* The scraper relies on **Playwright**, so the first run may download browsers automatically.
* Using **Method 1** is recommended for scalability and reproducibility.
* Already collected teams or competitions (for the same season) are **automatically skipped** to avoid redundant scraping.
* `typegame` and `spread` allow flexible control of scraping scope — from a single competition’s upcoming games to a full seasonal network of related competitions and teams.

---
