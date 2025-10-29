## 🧾 README

### Overview

This Python project allows you to scrape the match history of a **team** or a **competition** from [oddsPortal.com](https://www.oddsportal.com).

It provides detailed information for a given **sport**, **team**, or **competition** during a specific **season**.

---

### 📊 Collected Data

#### For a competition:

In addition to the general information provided by the user (`season`, `bookmaker`, `market`, `region`, `competition`, `sport`), the script collects the following data for each match:

* Match score
* Home team
* Away team
* Opening and closing odds (value, date, and time) for outcome **1** in the **1X2** market
* Opening and closing odds (value, date, and time) for outcome **X** (if available)
* Opening and closing odds (value, date, and time) for outcome **2** in the **1X2** market

Furthermore, when retrieving the history of a **competition**, the script also:

* Fetches the **match history of all teams** that participated in that competition during the specified season.
* Collects the **history of other competitions** that these teams played in during the same season.
* **Skips** any team or competition from that season if its data **already exists** in the `scraped_data/` directory — avoiding redundant scraping and saving time.

This provides a **complete overview of the season** for both the competition and all teams involved.

#### For a team:

In addition to the same information collected for competitions, each match entry also includes:

* The **region** where the competition takes place
* The **competition** name

⚠️ The odds are retrieved according to the specified bookmaker.

---

### ⚙️ Requirements

* **Python 3.x**
* **Playwright**

---

### 💻 Installation

```bash
git clone https://github.com/djibril-marega/oddsportal_scraper.git
cd my-project
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

You can find the `teamid` in the team’s URL on oddsPortal:
Example: `https://www.oddsportal.com/football/team/psg/CjhkPw0k/` → `teamid` = `CjhkPw0k`

Example for a **competition**:

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

You can mix both teams and competitions in the same JSON list — there’s no limit to the number of entries.

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

Run directly with pytest:

```bash
pytest test_oddsportal.py --sport=Football --region=France --competition="Ligue 1" --season=2021/2022 --bookmaker=Betclic -v --tb=short
```

Options:

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
* Using Method 1 is strongly recommended for scalability and reproducibility.
* Already collected teams or competitions (for the same season) are **automatically skipped** to prevent redundant data collection.

---
