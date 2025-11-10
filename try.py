from typing import List, Dict, Any
import requests
import json
import re
import pandas as pd
from openpyxl.workbook import Workbook
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
#3. Define Base URL
url = 'https://events.informamarkets.com/content/data/informa/lov/data.eventEditions.expanded.json?sort=/eventStartDate,/eventEndDate&filter=%24%5B%3F(%40.eventEndDate%3E%3D%272025-10-28%27%20%26%26%20%40.infcomDisplay%3D~%2F%5EY%5Bes%5D%3F%24%2Fi)%5D&limit=30&page='
# 2. Initialize
pg_num = 1
all_events = []

# 3. Pagination Loop
while True:
    response = requests.get(url.format(pg_num), headers=headers)
    print(f"Page {pg_num}: {response.status_code}")

    if response.status_code != 200:
        print("Error fetching data.")
        break

    data = response.json()
    items = data.get('items', [])

    # Stop if no more items
    if not items:
        print("No more items found.")
        break

    # 4. Extract desired fields
    for event in items:
        event_info = {
            "eventName": event.get("eventEditionLongName"),
            "shortName": event.get("eventEditionShortName"),
            "city": event.get("cityFreeText"),
            "country": event.get("locationCountry"),
            "startDate": event.get("eventStartDate"),
            "endDate": event.get("eventEndDate"),
            "url": event.get("URL"),
        }
        all_events.append(event_info)

    # 5. Check if there are more pages
    count = data.get("count")
    total = data.get("total")

    # Stop if we've reached the last page
    if count * pg_num >= total:
        break

    pg_num += 1

# 6. Convert to DataFrame
df = pd.DataFrame(all_events)

# 7. Save as CSV and Excel
df.to_csv("events_data.csv", index=False, encoding='utf-8-sig')
df.to_excel("events_data.xlsx", index=False)

print(f"\n✅ Saved {len(df)} events to 'events_data.csv' and 'events_data.xlsx'")