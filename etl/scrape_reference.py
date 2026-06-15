import json
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA_SITE_URL = "https://otel-hackathon-data-site.vercel.app"
RAW_DIR = Path("etl/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

TABS = ["Room types", "Markets", "Channels", "Rate plans", "Macro history"]


def main():
    reference = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(f"{DATA_SITE_URL}/reference", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        for tab in TABS:
            page.locator("button", has_text=tab).click(timeout=10000)
            page.wait_for_timeout(700)

            text = page.locator("body").inner_text()
            reference[tab] = text

            print(f"Scraped tab: {tab}")

        browser.close()

    (RAW_DIR / "reference_raw.json").write_text(json.dumps(reference, indent=2))
    print("Wrote etl/raw/reference_raw.json")


if __name__ == "__main__":
    main()