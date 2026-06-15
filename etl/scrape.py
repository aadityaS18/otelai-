import hashlib
import json
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA_SITE_URL = "https://otel-hackathon-data-site.vercel.app"
RAW_DIR = Path("etl/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def sha256_ids(reservation_ids):
    text = "\n".join(sorted(reservation_ids)) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_ids_from_links(page):
    ids = []
    links = page.locator("a").all()

    for link in links:
        href = link.get_attribute("href") or ""
        if href.startswith("/reservations/R"):
            reservation_id = href.split("/")[-1]
            ids.append(reservation_id)

    return ids


def scrape_reservation_ids(page):
    reservation_ids = []
    pages_scraped = 0

    page.goto(f"{DATA_SITE_URL}/reservations", wait_until="networkidle")

    while True:
        ids_on_page = extract_ids_from_links(page)

        if not ids_on_page:
            break

        pages_scraped += 1
        reservation_ids.extend(ids_on_page)
        print(f"List page {pages_scraped}: {len(ids_on_page)} reservations")

        next_button = page.get_by_role("button", name="Next →")

        if next_button.count() == 0 or next_button.first.is_disabled():
            break

        first_id_before = ids_on_page[0]

        next_button.first.click()
        page.wait_for_function(
            """firstId => {
                const links = Array.from(document.querySelectorAll('a'));
                const reservationLinks = links
                    .map(a => a.getAttribute('href') || '')
                    .filter(h => h.startsWith('/reservations/R'));
                return reservationLinks.length > 0 &&
                       !reservationLinks[0].endsWith(firstId);
            }""",
            arg=first_id_before,
        )

    return sorted(set(reservation_ids)), pages_scraped


def scrape_reservation_details(page, reservation_ids):
    details = []

    for index, reservation_id in enumerate(reservation_ids, start=1):
        url = f"{DATA_SITE_URL}/reservations/{reservation_id}"

        loaded = False

        for attempt in range(3):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector("text=RESERVATION FIELDS", timeout=20000)
                loaded = True
                break
            except Exception as exc:
                print(f"Retry {attempt + 1}/3 for {reservation_id}: {exc}")
                page.wait_for_timeout(1000)

        if not loaded:
            raise RuntimeError(f"Failed to load detail page for {reservation_id}")

        body_text = page.locator("body").inner_text()

        details.append({
            "reservation_id": reservation_id,
            "url": url,
            "text": body_text,
        })

        print(f"Detail {index}/{len(reservation_ids)}: {reservation_id}")

    return details


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        reservation_ids, pages_scraped = scrape_reservation_ids(page)
        details = scrape_reservation_details(page, reservation_ids)

        browser.close()

    manifest = {
        "anchor_date": str(date.today()),
        "pages_scraped": pages_scraped,
        "reservation_ids_count": len(reservation_ids),
        "reservation_ids_sha256": sha256_ids(reservation_ids),
        "source_url": f"{DATA_SITE_URL}/reservations",
    }

    (RAW_DIR / "reservation_ids.json").write_text(
        json.dumps(reservation_ids, indent=2)
    )

    (RAW_DIR / "reservation_details_raw.json").write_text(
        json.dumps(details, indent=2)
    )

    Path("etl/SCRAPE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2)
    )

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()