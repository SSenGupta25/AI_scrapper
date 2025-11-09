'THE BASIC CONCEPT'

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import random

# Change this to your actual URL
BASE_URL = "https://events.informamarkets.com/en/event-listing.html"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


async def fetch_rendered_html():
    """Load the full rendered page using Playwright (stealth mode)."""
    user_agent = random.choice(USER_AGENTS)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        print(f"🌐 Loading {BASE_URL} ...")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

        # Wait extra time to ensure JS content has loaded
        await asyncio.sleep(5)

        html = await page.content()
        await browser.close()
        return html


def parse_events(html):
    """Parse event cards from Informa Markets <div class='event-item'> structure."""
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.event-item")
    print(f"✅ Found {len(cards)} event cards.")

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
            date = f"{start_date} - {end_date}"
        elif start_date:
            date = start_date
        else:
            date = None

        # Region (optional)
        region = card.get("data-region")

        events.append({
            "title": title,
            "date": date,
            "location": location,
            "region": region,
            "event_page": event_page,
            "image_url": image_url,
        })

    return events


async def main():
    html = await fetch_rendered_html()
    events = parse_events(html)

    print(f"\n🎉 Extracted {len(events)} events.\n")

    # Save to JSON
    with open("events_duesseldorf.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print("💾 Saved to events_duesseldorf.json")


if __name__ == "__main__":
    asyncio.run(main())
