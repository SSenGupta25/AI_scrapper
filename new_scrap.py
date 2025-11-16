import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import re
from groq import Groq

# ---- CONFIG ----
client = Groq(api_key="")

# Example card HTML for schema generation
EXAMPLE_CARD_HTML = """
<div class="card-digitalprofile-bottom">
    <p class="card-digitalprofile-name">CAFE' CENTRO BRASIL VITTORIO WURZBURGER SAS &amp; C. </p>
    <div class="card-digitalprofile-position-category">
        <div class="card-digitalprofile-position">
            <p>POSITION</p>
            <p class="line-clamp-2">A1/161</p>
        </div>
    </div>
    <p class="card-digitalprofile-cta-wrapper">
        <a href="/en/profile-detail/CAFE%20CENTRO%20BRASIL%20VITTORIO%20WURZBURGER%20SAS%20%20C?digitalProfileId=1182718"
           class="btn btn-plain size-sm"
           aria-label="show">
            <span class="label">show</span>
            <span class="material-icons-outlined icon">arrow_forward</span>
        </a>
    </p>
</div>
"""

# ============================================================
# INPUT URL & PAGINATION TYPE
# ============================================================
BASE_URL = input("Enter website URL: ").strip()

print("Pagination type options:")
print("1 = infinite_scroll")
print("2 = load_more_button")
print("3 = load_more_link")

pagination_options = {
    "1": "infinite_scroll",
    "2": "load_more_button",
    "3": "load_more_link"
}

user_input = input("Enter pagination type: ").strip()
PAGINATION_TYPE = pagination_options.get(user_input, "infinite_scroll")
print(f"Using pagination type: {PAGINATION_TYPE}")

# ============================================================
#   FETCH HTML WITH AUTO-PAGINATION (Updated for Load More + Cookie Modal)
# ============================================================
async def fetch_rendered_html(schema, pagination_type="infinite_scroll"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"🌐 Loading {BASE_URL} ...")
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)

        # --------------------------
        # Accept cookie modal if exists
        # --------------------------
        try:
            cookie_btn = await page.query_selector(
                "button#onetrust-accept-btn-handler, button.cookie-accept, button[data-cookie='accept']"
            )
            if cookie_btn:
                print("🍪 Closing cookie modal...")
                await cookie_btn.click()
                await asyncio.sleep(1)  # wait for modal to disappear
        except Exception as e:
            print(f"ℹ️ No cookie modal found or failed to close: {e}")

        prev_card_count = 0
        max_cycles = 50

        print("🔄 Pagination started...")

        for cycle in range(max_cycles):
            print(f"\n=== Pagination cycle {cycle + 1} ===")

            # --------------------------
            # Handle different pagination types
            # --------------------------
            if pagination_type == "load_more_button":
                btn = await page.query_selector("div.load-more-wrapper button.load-more")
                if btn:
                    await btn.scroll_into_view_if_needed()
                    print("➕ Clicking Load More button")
                    try:
                        await btn.click(timeout=10000)
                        await asyncio.sleep(2)  # wait for new cards to load
                    except Exception as e:
                        print(f"⚠️ Failed to click Load More button: {e}")
                else:
                    print("ℹ️ No Load More button found")

            elif pagination_type == "load_more_link":
                link = await page.query_selector("a.load-more, a.event-items-list-action-load-more")
                if link:
                    await link.scroll_into_view_if_needed()
                    print("➕ Clicking Load More link")
                    try:
                        await link.click(timeout=10000)
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"⚠️ Failed to click Load More link: {e}")
                else:
                    print("ℹ️ No Load More link found")

            elif pagination_type == "infinite_scroll":
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            # --------------------------
            # Count current cards
            # --------------------------
            current_card_count = await page.evaluate(
                f"document.querySelectorAll('{schema['card_selector']}').length"
            )
            print(f"📊 Total cards now: {current_card_count}")

            if current_card_count == prev_card_count:
                print("✅ No more new cards, stopping pagination.")
                break

            prev_card_count = current_card_count

        print("📦 Extracting fully rendered HTML...")
        html = await page.content()
        await browser.close()
        return html

# ============================================================
# GENERATE CARD SCHEMA
# ============================================================
def generate_card_schema(example_card_html):
    prompt = f"""
    You are an HTML structure analysis expert.

    I will give you ONE repeating card element HTML.
    Identify the correct CSS selector for all cards on the page.
    Identify child selectors for:
       - title / name
       - description
       - link
       - image
       - metadata (booth number, hall, role, country, etc.)

    Do NOT invent selectors.

    Return JSON ONLY:

    {{
      "card_selector": "CSS SELECTOR",
      "fields": {{
         "title": "CSS OR null",
         "link": "CSS OR null",
         "image": "CSS OR null",
         "metadata": {{
             "ROLE": "CSS OR null",
             "CITY": "CSS OR null",
             "COUNTRY": "CSS OR null",
             "BOOTH": "CSS OR null"
          }}
      }}
    }}

    HTML example:
    {example_card_html}
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    raw = response.choices[0].message.content
    match = re.search(r"```json(.*?)```", raw, re.S)
    json_text = match.group(1).strip() if match else raw

    try:
        return json.loads(json_text)
    except Exception:
        cleaned = re.sub(r"[^{}:,\"\[\]A-Za-z0-9_\-\s./]", "", json_text)
        return json.loads(cleaned)

# ============================================================
# PARSE CARDS
# ============================================================
def parse_cards(html, schema):
    soup = BeautifulSoup(html, "html.parser")
    card_selector = schema.get("card_selector")
    fields = schema.get("fields", {})

    cards = soup.select(card_selector)
    print(f"🔍 Found {len(cards)} cards using selector: {card_selector}")

    results = []
    for card in cards:
        item = {}

        # Title
        sel = fields.get("title")
        if sel:
            tag = card.select_one(sel)
            item["title"] = tag.get_text(strip=True) if tag else None

        # Link
        sel = fields.get("link")
        link = None
        if sel:
            tag = card.select_one(sel)
            if tag:
                link = tag.get("href") or tag.get("data-href")
        item["link"] = link

        # Image
        sel = fields.get("image")
        img = None
        if sel:
            tag = card.select_one(sel)
            if tag:
                img = tag.get("src") or tag.get("data-src")
        item["image"] = img

        # Metadata
        metadata_schema = fields.get("metadata", {})
        metadata = {}
        for key, sel in metadata_schema.items():
            tag = card.select_one(sel) if sel else None
            metadata[key] = tag.get_text(strip=True) if tag else None

        item["metadata"] = metadata
        results.append(item)

    return results

# ============================================================
# MAIN
# ============================================================
async def main():
    print("🧠 Requesting LLM schema...")
    schema = generate_card_schema(EXAMPLE_CARD_HTML)
    print("\n📜 Generated Schema:")
    print(json.dumps(schema, indent=2))

    html = await fetch_rendered_html(schema)
    print("\n🔧 Parsing cards...")
    items = parse_cards(html, schema)
    print(f"\n🎉 Extracted {len(items)} items.")

    with open("extracted_cards.json", "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print("💾 Saved → extracted_cards.json")

if __name__ == "__main__":
    asyncio.run(main())
