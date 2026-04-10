import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# Load product data
products = pd.read_csv("data/cleaned/combined_products.csv")

all_reviews = []

headers = {
    "User-Agent": "Mozilla/5.0"
}

for index, row in products.iterrows():
    name = row["title"]   # ✅ FIXED
    url = row["url"]

    print(f"Scraping: {name}")

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        review_elements = soup.find_all("span", {"data-hook": "review-body"})

        print("Found reviews:", len(review_elements))  # DEBUG

        for r in review_elements:
            review_text = r.get_text(strip=True)

            all_reviews.append({
                "product": name,
                "review": review_text
            })

        time.sleep(2)

    except Exception as e:
        print("Error:", e)

# Save reviews
df = pd.DataFrame(all_reviews)
df.to_csv("data/raw/reviews.csv", index=False)

print("✅ reviews.csv created")