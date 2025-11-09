'NO NEED TO USE'

import subprocess
import sys
import json

def main():
    # --- 1️⃣ User input ---
    base_url = input("Enter the base URL to scrape: ").strip()
    print("\nPaste one full example event HTML snippet below (end with an empty line):")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    example_html = "\n".join(lines)

    # --- 2️⃣ Save config for other scripts to use ---
    config = {
        "BASE_URL": base_url,
        "EXAMPLE_CARD_HTML": example_html
    }

    with open("scraper_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print("✅ Configuration saved to scraper_config.json")

    # --- 3️⃣ Run the scraper ---
    print("\n🚀 Running New_scrap.py ...")
    result_scraper = subprocess.run([sys.executable, "New_scrap.py"])
    if result_scraper.returncode != 0:
        print("❌ Error running New_scrap.py — aborting.")
        sys.exit(1)

    # --- 4️⃣ Run the enrichment script ---
    print("\n🧠 Running f.py (enrichment)...")
    result_enrich = subprocess.run([sys.executable, "f.py"])
    if result_enrich.returncode != 0:
        print("❌ Error running f.py.")
        sys.exit(1)

    print("\n🎉 All tasks completed successfully!")

if __name__ == "__main__":
    main()
