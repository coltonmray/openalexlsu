import requests
import json
import time
import os
import logging
from datetime import datetime, timezone

# -----------------------------
# CONFIG
# -----------------------------
BASE_URL = "https://api.openalex.org/works"
OUTPUT_FILE = "works.json"
STATE_FILE = "state.json"
RAW_DIR = "data/raw"

# Optional: filter example
FILTER = "institutions.id:I121820613"  # LSU
PER_PAGE = 200  # max allowed by OpenAlex

# Rate limiting
REQUEST_DELAY = 0.2  # seconds between requests

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -----------------------------
# STATE MANAGEMENT
# -----------------------------
def load_state():
    if not os.path.exists(STATE_FILE):
        logging.info("No state file found. Starting fresh.")
        return {"last_updated_date": None}

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# -----------------------------
# DATA LOADING
# -----------------------------
def load_existing_works():
    if not os.path.exists(OUTPUT_FILE):
        return []

    with open(OUTPUT_FILE, "r") as f:
        return json.load(f)


def save_works(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_raw_snapshot(data):
    os.makedirs(RAW_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    path = os.path.join(RAW_DIR, f"works_{timestamp}.json")

    with open(path, "w") as f:
        json.dump(data, f)

    logging.info(f"Saved raw snapshot: {path}")


# -----------------------------
# OPENALEX FETCH
# -----------------------------
def fetch_incremental(last_updated_date):
    all_results = []
    cursor = "*"

    params = {
        "filter": FILTER,
        "per-page": PER_PAGE,
        "cursor": cursor
    }

    if last_updated_date:
        params["filter"] += f",from_updated_date:{last_updated_date}"

    logging.info(f"Starting fetch with params: {params}")

    while True:
        response = requests.get(BASE_URL, params=params)

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        data = response.json()

        results = data.get("results", [])
        meta = data.get("meta", {})

        logging.info(f"Fetched {len(results)} records")

        if not results:
            break

        all_results.extend(results)

        cursor = meta.get("next_cursor")
        if not cursor:
            break

        params["cursor"] = cursor

        time.sleep(REQUEST_DELAY)

    logging.info(f"Total fetched: {len(all_results)}")
    return all_results


# -----------------------------
# MERGE / DEDUPE
# -----------------------------
def merge_works(existing, new):
    existing_by_id = {w["id"]: w for w in existing}

    added = 0
    updated = 0

    for work in new:
        work_id = work["id"]

        if work_id in existing_by_id:
            existing_by_id[work_id] = work  # overwrite (update)
            updated += 1
        else:
            existing_by_id[work_id] = work
            added += 1

    logging.info(f"Added: {added}, Updated: {updated}")

    return list(existing_by_id.values())


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def main():
    state = load_state()
    last_updated_date = state.get("last_updated_date")

    logging.info(f"Last updated date: {last_updated_date}")

    new_data = fetch_incremental(last_updated_date)

    if not new_data:
        logging.info("No new data retrieved. Exiting.")
        return

    existing_data = load_existing_works()

    merged_data = merge_works(existing_data, new_data)

    # Save outputs
    save_works(merged_data)
    save_raw_snapshot(new_data)

    # Update state
    new_timestamp = datetime.now(timezone.utc).isoformat()
    state["last_updated_date"] = new_timestamp
    save_state(state)

    logging.info("Pipeline complete.")


if __name__ == "__main__":
    main()
