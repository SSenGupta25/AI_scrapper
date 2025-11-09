'USE THIS FILE FOR DOING THE DESCRIPTION WRITING AND CONVERTING TO JSON, CSV, EXCEL FILES'

import json
import requests
from bs4 import BeautifulSoup
from groq import Groq
import time
import pandas as pd
# Initialize Groq client
client = Groq(api_key="")

# Input and output paths
input_path = "/Users/subhrajyotisengupta/Fiera Milano AI Scrapper/events_duesseldorf.json"
output_path = "/Users/subhrajyotisengupta/Fiera Milano AI Scrapper/events_duesseldorf_enriched.json"

# Step 1: Load the JSON
with open(input_path, "r") as file:
    events = json.load(file)

def scrape_text_from_url(url):
    """Fetch HTML content and extract readable text."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract visible text
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        text = " ".join(soup.stripped_strings)
        return text[:8000]  # limit to avoid token overflow
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def summarize_event(text, title):
    """Use Groq LLM to summarize the event description."""
    prompt = f"""
    You are a helpful assistant. Based on the following web content, 
    write a 2 sentence summary describing what the event '{title}' is about,
    its focus, and its audience in italian.

    Web content:
    {text}
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing {title}: {e}")
        return "Description unavailable."

# Step 2: Process each event
for event in events:
    print(f"Processing: {event['title']}")
    page_text = scrape_text_from_url(event["event_page"])
    if page_text:
        event["description"] = summarize_event(page_text, event["title"])
    else:
        event["description"] = "Description unavailable (failed to fetch page)."
    time.sleep(2)  # avoid rate limits

# Step 3: Save enriched JSON
with open(output_path, "w") as f:
    json.dump(events, f, indent=4)

print(f"✅ Enriched data saved to {output_path}")

# Load enriched data
with open(output_path, "r") as f:
    enriched_events = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(enriched_events)

# Save to CSV
csv_output_path = output_path.replace(".json", ".csv")
df.to_csv(csv_output_path, index=False, encoding="utf-8")
print(f"✅ CSV file saved to {csv_output_path}")

# Save to Excel
excel_output_path = output_path.replace(".json", ".xlsx")
df.to_excel(excel_output_path, index=False)
print(f"✅ Excel file saved to {excel_output_path}")