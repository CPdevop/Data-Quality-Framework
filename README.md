Data Quality Framework – README

A lightweight, config-driven, pandas-based data quality (DQ) framework that reads table-level/column-level rules from JSON, executes them against your source tables (PostgreSQL right now, easily extendable), and generates a single, attractive HTML report with run summary, table summary, and failed-check details.

1. Features

✅ Config-driven: each table has its own JSON file describing checks

✅ Table-level & column-level checks

✅ Built-in library of common DQ checks (not null, unique, regex, enum, PK dup, FK existence, numeric range, timestamp in past, no future dates, no blank strings…)

✅ Pandas execution layer → easy to debug and extend

✅ HTML report generated via Jinja2 template (dq_html_template.html)

✅ JSON run summary for automation/CI integration

✅ Timestamped reports saved to output/

✅ Extensible – just drop a new JSON in configs/ to onboard a new table

2. Project Structure
dq_framework_prod/
└── dq_framework/
    ├── dq_runner.py              # main entrypoint
    ├── dq_checks.py              # all reusable DQ check functions
    ├── dq_reporter.py            # HTML report writer using Jinja2
    ├── dq_html_template.html     # base template for beautiful report
    ├── configs/                  # per-table JSON configs
    │   ├── customers.json
    │   ├── accounts.json
    │   └── ...
    ├── output/                   # generated HTML + JSON summaries
    └── requirements.txt


Adjust paths if you extracted it somewhere else – but the idea is: runner → loads configs → runs checks → writes output.

3. How It Works (Flow)

Runner (dq_runner.py)

loads all *.json from configs/

creates a DB engine (Postgres via SQLAlchemy)

for each config → pulls data into pandas

executes all checks using functions in dq_checks.py

collects results into a single list

Reporter (dq_reporter.py)

aggregates totals: total checks, passed, failed, pass %

aggregates per-table summary

renders dq_html_template.html → final report in output/report_YYYYMMDD_HHMMSS.html

also dumps output/summary_YYYYMMDD_HHMMSS.json (for CI / Airflow / Databricks)

You open HTML → see cards: Total checks, Passed, Failed, Pass %, section “Checks by Table”, and a detailed failed-checks table.

4. Installation

Create virtual env (optional but good)

python -m venv venv
venv\Scripts\activate  # on Windows
# source venv/bin/activate  # on mac/linux


Install deps

pip install -r requirements.txt


Typical requirements.txt:

pandas
sqlalchemy
psycopg2-binary
jinja2
python-dateutil


(If you are running Python 3.13 and psycopg2 complains, install from wheel or use psycopg2 appropriate to your platform.)

5. Configure Database Connection

dq_runner.py currently creates SQLAlchemy engine from inline settings. Open dq_runner.py and set this section:

DB_CONFIG = {
    "user": "postgres",
    "password": "your_password",
    "host": "localhost",
    "port": 5432,
    "database": "synthetic_bank"
}


or, if you prefer env vars:

import os
DB_CONFIG = {
    "user": os.getenv("DQ_DB_USER", "postgres"),
    ...
}


We used PostgreSQL in your tests, but SQLAlchemy lets you switch to any DB that pandas can read from.

6. Config Files (core idea)

Each table has a JSON file in configs/. Example:

{
  "table_name": "accounts",
  "schema": "public",
  "business_name": "Customer Accounts Master",
  "primary_key": ["account_id"],
  "checks": [
    {
      "level": "column",
      "column": "account_id",
      "type": "not_null",
      "name": "ACCT_TC001_not_null_account_id",
      "severity": "HIGH"
    },
    {
      "level": "column",
      "column": "account_id",
      "type": "unique",
      "name": "ACCT_TC002_unique_account_id",
      "severity": "HIGH"
    },
    {
      "level": "column",
      "column": "account_number",
      "type": "regex",
      "pattern": "^[0-9]{10,16}$",
      "name": "ACCT_TC003_regex_account_number",
      "severity": "MEDIUM"
    },
    {
      "level": "table",
      "type": "row_count_gt",
      "threshold": 0,
      "name": "ACCT_TC004_rowcount_gt_zero",
      "severity": "LOW"
    }
  ]
}


Keys:

level: "table" or "column"

type: the DQ rule. It must match a function in dq_checks.py

name: appears in HTML

severity: just for reporting

extra fields (like pattern, threshold, values) are passed straight into the check function

7. Built-in Checks (in dq_checks.py)

We added/mentioned these:

Column-level

not_null

unique

regex

allowed_values / enum

no_whitespace (no ' ' or empty strings)

min_value / max_value

numeric_range (min & max)

timestamp_not_in_future

timestamp_not_before (if needed)

length_between (optional)

fk_exists (if you load lookup table in same run)

Table-level

row_count_gt

no_duplicate_pk (based on primary_key)

no_duplicate_hash (if hash column given)

Each check returns a dict like:

{
  "table": "accounts",
  "check_name": "ACCT_TC002_unique_account_id",
  "level": "column",
  "column": "account_id",
  "status": "PASS" or "FAIL",
  "failed_count": 3,
  "sample_rows": [...],
  "details": "3 duplicate account_id found",
  "severity": "HIGH"
}


The runner collects these.

8. Running the Framework

From inside dq_framework folder:

python dq_runner.py


What it does:

reads all JSON in configs/

runs all checks

writes:

output/report_20251031_183000.html

output/summary_20251031_183000.json

You saw this line earlier:

run_at: {{ run_at }} | Tables: {{ total_tables }} | Checks: {{ total_checks }} | ...


in the template — that gets replaced during render.

9. HTML Report

We used a simple Jinja2 template with cards on top and tables below.

Top section shows:

Total Checks

Passed

Failed

Pass %

Then:

Checks by Table (table name, total, passed, failed)

Detailed Checks (each check, status, column, failed count, notes)

You can style this more — it’s just HTML/CSS. Your screenshot had the teal header ✔

10. Handling Pandas Timestamp Issue

You hit this earlier:

TypeError: Invalid comparison between dtype=datetime64[ns] and datetime

We fixed it by making the DQ check timezone-aware safe:

from datetime import datetime, timezone

def check_timestamp_not_in_future(df, table, column, cfg):
    if column not in df.columns:
        return _fail_missing_column(...)
    ser = pd.to_datetime(df[column], errors="coerce")
    now = datetime.now(timezone.utc)
    mask = ser.notnull() & (ser.dt.tz_localize("UTC", nonexistent="shift_forward", ambiguous="NaT")
                            > now)
    ...


and in dq_runner.py we also converted pandas Timestamp to string before dumping JSON:

# before json.dump(...)
for r in all_results:
    if isinstance(r.get("run_at"), pd.Timestamp):
        r["run_at"] = r["run_at"].isoformat()


So the framework is now safe to dump.

11. Adding a New Table

Create configs/your_table.json

Add table name, schema, primary key, checks

Run:

python dq_runner.py --table your_table   # if you add arg parsing
# or just:
python dq_runner.py                      # it will pick all jsons


That’s it — no Python change needed.

12. Extending with Custom Checks

Open dq_checks.py

Add a function:

def check_email_domain(df, table, column, cfg):
    allowed = cfg.get("allowed_domains", [])
    ...


Add to dispatcher (if you used one):

CHECK_REGISTRY = {
    "not_null": check_not_null,
    ...
    "email_domain": check_email_domain,
}


Use it in JSON:

{
  "level": "column",
  "column": "email",
  "type": "email_domain",
  "allowed_domains": ["gmail.com", "mcafee.com"],
  "name": "CUST_TC010_email_domain_check",
  "severity": "LOW"
}

13. CI / Scheduled Run (example)

You can run it every night from a scheduler (Windows Task Scheduler, Airflow, Databricks job, GitHub Action):

python dq_runner.py && echo "DQ run completed"


Then publish output/*.html to S3 / SharePoint / internal portal.

14. Known Limitations / To-Dos

right now it loads full table into pandas → for very large tables use:

sampling

LIMIT in config

or change to SQL-pushdown checks

only Postgres tested

no email/slack notifier yet (easy to add on top of JSON summary)

template is single-page; can be split by table

15. Quickstart (TL;DR)
git clone <your-repo>
cd dq_framework_prod/dq_framework
pip install -r requirements.txt
# edit configs/*.json
# edit DB_CONFIG in dq_runner.py
python dq_runner.py
start output/report_*.html   # on Windows
