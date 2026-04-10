"""
amazon_scraper.py
Scrapes product listings and customer reviews from Amazon India
for specified luggage brands using Playwright.
"""

import asyncio
import json
import random
import re
import time
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ── Config ────────────────────────────────────────────────────────────────────
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

BRANDS = [
    "Safari",
    "Skybags",
    "American Tourister",
    "VIP",
    "Aristocrat",
    "Nasher Miles",
]

MAX_PRODUCTS_PER_BRAND = 12
MAX_REVIEWS_PER_PRODUCT = 60
REVIEW_PAGES = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def random_delay(min_s=2.5, max_s=5.5):
    return random.uniform(min_s, max_s)


def parse_price(text: str) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_rating(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"(\d+\.?\d*)", text)
    return float(m.group(1)) if m else None


def parse_review_count(text: str) -> int:
    if not text:
        return 0
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else 0


# ── Product scraping ──────────────────────────────────────────────────────────

async def scrape_search_page(page, brand: str, page_num: int = 1) -> list[str]:
    """Return list of ASINs from a search results page."""
    query = brand.replace(" ", "+") + "+luggage+trolley+bag"
    url = f"https://www.amazon.in/s?k={query}&page={page_num}"

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random_delay(3, 6))

        # Scroll to trigger lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1.5)

        # Collect all product cards with a valid ASIN
        cards = await page.query_selector_all("[data-asin]")
        asins = []
        for card in cards:
            asin = await card.get_attribute("data-asin")
            if asin and len(asin) == 10:
                asins.append(asin)

        return list(dict.fromkeys(asins))  # deduplicate preserving order

    except PlaywrightTimeout:
        print(f"  [timeout] search page {page_num} for {brand}")
        return []


async def scrape_product_page(page, asin: str, brand: str) -> dict | None:
    """Scrape a single product listing page."""
    url = f"https://www.amazon.in/dp/{asin}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random_delay(2, 4))

        # Title
        title_el = await page.query_selector("#productTitle")
        title = (await title_el.inner_text()).strip() if title_el else ""

        # Selling price
        price_el = await page.query_selector(".a-price .a-offscreen")
        price_text = (await price_el.inner_text()).strip() if price_el else ""

        # MRP / list price
        mrp_el = await page.query_selector(
            ".a-text-price .a-offscreen, #priceblock_ourprice_lbl + span"
        )
        mrp_text = (await mrp_el.inner_text()).strip() if mrp_el else ""

        # Try alternate MRP selector
        if not mrp_text:
            mrp_el2 = await page.query_selector("span.a-price.a-text-price span.a-offscreen")
            if mrp_el2:
                mrp_text = (await mrp_el2.inner_text()).strip()

        # Rating
        rating_el = await page.query_selector("#acrPopover .a-icon-alt, span[data-hook='rating-out-of-text']")
        rating_text = (await rating_el.inner_text()).strip() if rating_el else ""

        # Review count
        rc_el = await page.query_selector("#acrCustomerReviewText")
        rc_text = (await rc_el.inner_text()).strip() if rc_el else ""

        # Discount badge
        discount_el = await page.query_selector(".savingsPercentage, .a-color-price")
        discount_text = (await discount_el.inner_text()).strip() if discount_el else ""

        # Category / size from title
        size_tag = _infer_size(title)

        price = parse_price(price_text)
        mrp = parse_price(mrp_text)

        # Compute discount % if not found in badge
        discount_pct = None
        if discount_text:
            m = re.search(r"(\d+)\s*%", discount_text)
            if m:
                discount_pct = float(m.group(1))
        if discount_pct is None and price and mrp and mrp > price:
            discount_pct = round((mrp - price) / mrp * 100, 1)

        return {
            "asin": asin,
            "brand": brand,
            "title": title,
            "price": price,
            "mrp": mrp,
            "discount_pct": discount_pct,
            "rating": parse_rating(rating_text),
            "review_count": parse_review_count(rc_text),
            "size_tag": size_tag,
            "url": url,
        }

    except PlaywrightTimeout:
        print(f"  [timeout] product {asin}")
        return None
    except Exception as e:
        print(f"  [error] product {asin}: {e}")
        return None


def _infer_size(title: str) -> str:
    title_lower = title.lower()
    if "cabin" in title_lower or "20\"" in title_lower or "20 inch" in title_lower:
        return "cabin"
    if "medium" in title_lower or "24\"" in title_lower or "24 inch" in title_lower:
        return "medium"
    if "large" in title_lower or "28\"" in title_lower or "28 inch" in title_lower or "30 inch" in title_lower:
        return "large"
    if "set" in title_lower or "combo" in title_lower or "piece" in title_lower:
        return "set"
    return "unknown"


# ── Review scraping ───────────────────────────────────────────────────────────

async def scrape_reviews(page, asin: str, max_reviews: int = MAX_REVIEWS_PER_PRODUCT) -> list[dict]:
    """Paginate through review pages and collect reviews."""
    all_reviews = []

    for page_num in range(1, REVIEW_PAGES + 1):
        if len(all_reviews) >= max_reviews:
            break

        url = (
            f"https://www.amazon.in/product-reviews/{asin}"
            f"?pageNumber={page_num}&reviewerType=all_reviews&sortBy=recent"
        )

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random_delay(2.5, 5))

            review_blocks = await page.query_selector_all("[data-hook='review']")
            if not review_blocks:
                break

            for block in review_blocks:
                review = await _parse_review_block(block)
                if review:
                    all_reviews.append(review)

        except PlaywrightTimeout:
            print(f"  [timeout] reviews page {page_num} for {asin}")
            break
        except Exception as e:
            print(f"  [error] reviews {asin} p{page_num}: {e}")
            break

    return all_reviews[:max_reviews]


async def _parse_review_block(block) -> dict | None:
    try:
        # Star rating
        rating_el = await block.query_selector("[data-hook='review-star-rating'] .a-icon-alt")
        rating_text = (await rating_el.inner_text()).strip() if rating_el else ""

        # Title
        title_el = await block.query_selector("[data-hook='review-title'] span:not(.a-icon-alt)")
        review_title = (await title_el.inner_text()).strip() if title_el else ""

        # Body
        body_el = await block.query_selector("[data-hook='review-body'] span")
        body = (await body_el.inner_text()).strip() if body_el else ""

        # Date
        date_el = await block.query_selector("[data-hook='review-date']")
        date_text = (await date_el.inner_text()).strip() if date_el else ""

        # Verified purchase
        vp_el = await block.query_selector("[data-hook='avp-badge']")
        verified = vp_el is not None

        if not body:
            return None

        return {
            "rating": parse_rating(rating_text),
            "title": review_title,
            "body": body,
            "date": date_text,
            "verified": verified,
        }
    except Exception:
        return None


# ── Main orchestrator ─────────────────────────────────────────────────────────

async def scrape_brand(brand: str, browser):
    """Scrape all products + reviews for one brand."""
    print(f"\n{'='*50}")
    print(f"  Scraping brand: {brand}")
    print(f"{'='*50}")

    ctx = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1366, "height": 768},
        locale="en-IN",
        extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
    )
    page = await ctx.new_page()

    # Collect ASINs from first 2 search pages
    all_asins = []
    for pg in range(1, 3):
        asins = await scrape_search_page(page, brand, pg)
        all_asins.extend(asins)
        if len(all_asins) >= MAX_PRODUCTS_PER_BRAND:
            break
        await asyncio.sleep(random_delay())

    all_asins = list(dict.fromkeys(all_asins))[:MAX_PRODUCTS_PER_BRAND]
    print(f"  Found {len(all_asins)} products")

    brand_data = {"brand": brand, "products": []}

    for i, asin in enumerate(all_asins):
        print(f"  [{i+1}/{len(all_asins)}] Product {asin}")

        product = await scrape_product_page(page, asin, brand)
        if not product:
            continue

        await asyncio.sleep(random_delay(3, 6))

        print(f"    Scraping reviews...")
        reviews = await scrape_reviews(page, asin)
        product["reviews"] = reviews
        print(f"    Got {len(reviews)} reviews")

        brand_data["products"].append(product)

        # Save incrementally so progress isn't lost on crash
        _save_raw(brand, brand_data)

        await asyncio.sleep(random_delay(4, 8))

    await ctx.close()
    return brand_data


def _save_raw(brand: str, data: dict):
    fname = brand.lower().replace(" ", "_") + ".json"
    path = RAW_DIR / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved → {path}")


async def run_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # set True after confirming it works
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )

        for brand in BRANDS:
            # Skip if already scraped
            fname = brand.lower().replace(" ", "_") + ".json"
            if (RAW_DIR / fname).exists():
                print(f"  [skip] {brand} already scraped")
                continue

            brand_data = await scrape_brand(brand, browser)
            print(f"  Done: {brand} — {len(brand_data['products'])} products")

            # Longer pause between brands to avoid rate limiting
            await asyncio.sleep(random_delay(15, 30))

        await browser.close()
    print("\n All brands scraped!")


if __name__ == "__main__":
    asyncio.run(run_all())