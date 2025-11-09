'USE THIS FILE FOR SCRAPING THE EVENTS FROM THE WEBSITE AND SAVING IT TO A JSON FILE WITH THE FIRST ELEMENT'

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import re
from groq import Groq

# ---- CONFIG ----
client = Groq(api_key="")
BASE_URL = "https://events.informamarkets.com/en/event-listing.html"

# Paste your example event card HTML here
EXAMPLE_CARD_HTML = """
<div class="event-item event-item-id-UBM25DVT" data-start-date="2025-11-05" data-end-date="2025-11-07" data-city="Ho Chi Minh City" data-country="Vietnam" data-region="Asia">
  <div class="event-logo item-logo">
    <img class="event-logo-image item-logo-image" src="/content/dam/Informa/informa-markets/events-logos/VIET-DATA-CONFEX.png" alt="Data Center Vietnam">
  </div>
  <div class="event-data item-data">
    <span class="item-name event-name event-title has-logo">Vietnam Data Center & Cloud Confex</span>
    <div class="event-dates item-dates">
      <span class="event-start-date item-start-date">05</span>
      <span class="event-date-separator item-date-separator">-</span>
      <span class="event-end-date item-end-date">07 November, 2025</span>
    </div>
    <div class="event-location item-location">
      <span class="event-location-city item-location-city first">Ho Chi Minh City</span>
      <span class="event-location-separator item-location-separator">,</span>
      <span class="event-location-state item-location-state">Ho Chi Minh City</span>
      <span class="event-location-country item-location-country">Vietnam</span>
    </div>
  </div>
  <div class="event-actions item-actions actions">
    <a class="event-website item-website website" target="_blank" href="https://vietnamdatacentercloud.com/en/">View Event Site</a>
  </div>
</div>
"""


async def fetch_rendered_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        
        print("🌐 Page loaded. Waiting for first batch of events...")
        await page.wait_for_selector(".event-item", timeout=20000)

        last_count = 0
        same_count = 0

        while True:
            # Count current number of events
            current_count = await page.locator(".event-item").count()
            print(f"🔍 Current events: {current_count}")

            # Try clicking 'Load More' button if present
            load_more_btn = await page.query_selector("button, a")
            if load_more_btn:
                btn_text = (await load_more_btn.inner_text() or "").lower()
                if "load more" in btn_text or "show more" in btn_text:
                    try:
                        print("🖱️ Clicking 'Load More'...")
                        await load_more_btn.click()
                        await asyncio.sleep(3)  # wait for new events to load
                    except Exception:
                        pass

            # Check if new events loaded
            new_count = await page.locator(".event-item").count()
            if new_count == last_count:
                same_count += 1
            else:
                same_count = 0

            last_count = new_count

            # Stop if no new events after 2-3 checks
            if same_count >= 3:
                print("✅ All events loaded.")
                break

        html = await page.content()
        await browser.close()
        return html


def generate_parser_code(example_card_html):
    """Use the LLM to tweak/auto-generate the parser."""
    prompt = f"""
    You are a Python code assistant.
    I will give you the HTML of one event card from a web page.

    Your task is to update the following function so it correctly extracts data for all event cards on the same page.
    The code is defined below (fix syntax, selectors, etc.):

    ```python
    def parse_events(html):
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.select("div.event-item") or ('a.href') please select the one that is present in the provided HTML.
        print(f"✅ Found {{len(cards)}} event cards.")

        events = []
        for card in cards:
            # Title
            title_tag = card.select_one(".event-name, .item-name")
            title = title_tag.get_text(strip=True) if title_tag else None

            # Event website
            link_tag = card.select_one("a.event-website")
            event_page = link_tag["href"] if link_tag and link_tag.has_attr("href") else None

            # Image
            image_tag = card.select_one("img.event-logo-image")
            image_url = image_tag["src"] if image_tag and image_tag.has_attr("src") else None

            # Location
            city = card.get("data-city") or ""
            country = card.get("data-country") or ""
            location = ", ".join([v for v in [city, country] if v])

            # Dates
            start_date = card.get("data-start-date")
            end_date = card.get("data-end-date")
            if start_date and end_date:
                date = f"{{start_date}} - {{end_date}}"
            elif start_date:
                date = start_date
            else:
                date = None

            # Region (optional)
            region = card.get("data-region")

            events.append({{
                "title": title,
                "date": date,
                "location": location,
                "region": region,
                "event_page": event_page,
                "image_url": image_url,
            }})

        return events
    ```
    Just for "event_page", sometimes the HTML format have link entered inside 'href' of anchor tag directly.
    Also keep in mind the first HTML in JSON.
    Example event card HTML:
    {example_card_html}
    
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    code = response.choices[0].message.content
    match = re.search(r"```python(.*?)```", code, re.S)
    return match.group(1).strip() if match else code.strip()


async def main():
    html = await fetch_rendered_html()

    print("🧠 Generating parser code from your event card snippet...")
    parser_code = generate_parser_code(EXAMPLE_CARD_HTML)

    # Execute the generated parser code
    local_vars = {}
    exec(parser_code, globals(), local_vars)
    parse_events = local_vars.get("parse_events")

    print("✅ Parser function loaded. Now extracting events...")
    events = parse_events(html)

    print(f"\n🎉 Extracted {len(events)} events.\n")
    with open("events_duesseldorf.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print("💾 Saved to events_duesseldorf.json")


if __name__ == "__main__":
    asyncio.run(main())
