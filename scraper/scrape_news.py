#!/usr/bin/env python3
"""
Liest die aktuellen Regional-Nachrichten von mainwelle.de aus und schreibt
sie als JSON nach docs/news.json (wird von der Dashboard-Seite geladen).

Warum ein Headless-Browser (Playwright) und kein einfaches requests+BeautifulSoup?
Die Kategorieseite von mainwelle.de liefert den Artikel-Inhalt nicht im
initialen HTML aus, sondern lädt ihn per JavaScript nach. Ein normaler
HTTP-Request bekommt daher nur ein leeres Grundgerüst zu sehen.

Hinweis: Die Seite kann sich strukturell ändern. Falls der Scraper irgendwann
keine News mehr findet, schau dir per `python scrape_news.py --debug` das
gespeicherte debug_page.html an und pass die Selektoren unten an.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

SOURCE_URL = "https://www.mainwelle.de/kategorie/nachrichten/regional-nachrichten/"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "news.json"
MAX_ITEMS = 15
MAX_ATTEMPTS = 3

# Format wie auf der Seite beobachtet: "16 . Juli 2026 09:17 Überschrift..."
DATE_PATTERN = re.compile(
    r"(\d{1,2})\s*\.\s*"
    r"(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*"
    r"(\d{4})\s+(\d{2}):(\d{2})\s*(.*)",
    re.DOTALL,
)

# Dasselbe Muster als reines JS-Fragment, um im Browser per wait_for_function
# zu prüfen, ob schon "echte" Artikel-Links im DOM stehen (statt blind eine
# feste Zeit zu warten).
DATE_PATTERN_JS = (
    r"/\d{1,2}\s*\.\s*"
    r"(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*"
    r"\d{4}\s+\d{2}:\d{2}/"
)

MONTHS = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
    "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11,
    "Dezember": 12,
}


def parse_item(text: str, href: str):
    # search() statt match(): der Linktext beginnt inzwischen oft mit einer
    # Bildquellen-Angabe (z. B. "Landkreis Bayreuth") VOR dem Datum, daher
    # darf das Datumsmuster nicht zwingend am Textanfang stehen.
    match = DATE_PATTERN.search(text.strip())
    if not match:
        return None
    day, month_name, year, hour, minute, headline = match.groups()
    headline = headline.strip(" -–\n\t")
    if not headline or len(headline) < 4:
        return None
    try:
        published = datetime(
            int(year), MONTHS[month_name], int(day), int(hour), int(minute)
        )
    except ValueError:
        return None
    return {
        "title": headline,
        "published": published.isoformat(),
        "url": href,
    }


def collect_items(page):
    """Liest alle Links von der aktuell geladenen Seite und parst die, die
    wie ein Nachrichten-Eintrag aussehen."""
    anchors = page.eval_on_selector_all(
        "a",
        "els => els.map(e => ({text: e.innerText, href: e.href}))",
    )

    seen_urls = set()
    items = []
    for a in anchors:
        text = (a.get("text") or "").strip()
        href = a.get("href") or ""
        if not text or not href:
            continue
        item = parse_item(text, urljoin(SOURCE_URL, href))
        if item and item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            items.append(item)
    return items


def scrape(debug: bool = False):
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="de-DE")

        for attempt in range(1, MAX_ATTEMPTS + 1):
            page.goto(SOURCE_URL, wait_until="networkidle", timeout=30000)

            # Statt blind eine feste Zeit zu warten: aktiv darauf warten,
            # dass mindestens ein Link mit dem erwarteten Datumsmuster im
            # sichtbaren Text auftaucht. Das ist robuster gegen schwankende
            # Ladezeiten von Vue.js / des Cookie-Consent-Skripts.
            try:
                page.wait_for_function(
                    """(pattern) => {
                        const re = new RegExp(pattern);
                        return Array.from(document.querySelectorAll('a'))
                            .some(a => re.test(a.innerText || ''));
                    }""",
                    arg=DATE_PATTERN_JS.strip("/"),
                    timeout=10000,
                )
            except Exception:
                pass  # wird unten anhand der geparsten Items geprüft

            # Der Seite noch etwas Luft geben, falls weitere Artikel
            # nachgeladen werden, nachdem der erste sichtbar wurde.
            page.wait_for_timeout(1000)

            if debug:
                Path("debug_page.html").write_text(page.content(), encoding="utf-8")

            attempt_items = collect_items(page)

            if attempt_items:
                items = attempt_items
                break

            print(
                f"Versuch {attempt}/{MAX_ATTEMPTS}: keine Meldungen gefunden, "
                "versuche es erneut...",
                file=sys.stderr,
            )

        browser.close()

    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:MAX_ITEMS]


def main():
    debug = "--debug" in sys.argv
    items = scrape(debug=debug)

    if not items:
        # Kein Absturz, aber deutliche Fehlermeldung im Action-Log, damit man
        # es merkt, statt still eine leere Seite zu veröffentlichen.
        print("WARNUNG: Keine Nachrichten gefunden. Selektoren pruefen "
              "(python scraper/scrape_news.py --debug).", file=sys.stderr)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": SOURCE_URL,
        "items": items,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{len(items)} Meldungen geschrieben nach {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
