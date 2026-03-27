import requests
import json
import time

ROR_ID = "05ect4e57"
START_YEAR = 2020
BASE_URL = "https://api.openalex.org"

FIELDS = ",".join([
    "id",
    "title",
    "publication_year",
    "cited_by_count",
    "primary_location",
    "open_access",
    "type",
    "doi",
    "apc_list",
    "publication_date",
    "primary_topic",
    "authorships"
])

def fetch_all_works():
    all_results = []
    cursor = "*"

    filter_str = f"institutions.ror:{ROR_ID},from_publication_date:{START_YEAR}-01-01"

    while True:
        params = {
            "filter": filter_str,
            "per-page": 200,
            "cursor": cursor,
            "select": FIELDS,
            "sort": "publication_year:desc",
            "mailto": "lsulibrary@lsu.edu"
        }

        response = requests.get(f"{BASE_URL}/works", params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        all_results.extend(results)

        total = data.get("meta", {}).get("count", 0)
        print(f"Fetched {len(all_results)}/{total}")

        cursor = data.get("meta", {}).get("next_cursor")

        if not results or not cursor:
            break

        time.sleep(0.1)  # be polite to API

    return all_results


print("Fetching works from OpenAlex...")
works = fetch_all_works()

print(f"Total works: {len(works)}")

# Save compact JSON (important!)
with open("works.json", "w", encoding="utf-8") as f:
    json.dump(works, f, separators=(",", ":"))

print("Saved to works.json")
