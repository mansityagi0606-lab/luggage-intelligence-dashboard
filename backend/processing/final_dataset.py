import pandas as pd
from collections import Counter
import re

# Load files
products = pd.read_csv(r"data/raw/products.csv")
reviews = pd.read_csv("data/reviews_with_sentiment.csv")

# -------- CLEAN --------
def clean_text(text):
    text = re.sub(r'[^\w\s]', '', str(text))
    return text.lower()

# -------- EXTRACT THEMES --------
def extract_words(texts):
    words = []
    for t in texts:
        t = clean_text(t)
        words.extend(t.split())
    return [w for w, c in Counter(words).most_common(10) if len(w) > 3][:5]

# -------- BRAND LEVEL --------
brand_data = []

for brand in reviews["brand"].unique():
    subset = reviews[reviews["brand"] == brand]

    avg_sentiment = subset["score"].mean()

    pros = extract_words(subset[subset["sentiment"]=="positive"]["review"])
    cons = extract_words(subset[subset["sentiment"]=="negative"]["review"])

    brand_data.append({
        "brand": brand,
        "avg_sentiment": round(avg_sentiment, 3),
        "top_pros": ", ".join(pros),
        "top_cons": ", ".join(cons)
    })

brand_df = pd.DataFrame(brand_data)

# -------- PRODUCT AGGREGATION --------
products["price"] = pd.to_numeric(products["price"], errors="coerce")
products["rating"] = pd.to_numeric(products["rating"], errors="coerce")

product_summary = products.groupby("brand").agg({
    "price": "mean",
    "rating": "mean",
    "review_count": "sum"
}).reset_index()

product_summary.columns = ["brand", "avg_price", "avg_rating", "total_reviews"]

# -------- MERGE --------
final_df = pd.merge(product_summary, brand_df, on="brand")

# BONUS: value score
final_df["value_score"] = final_df["avg_sentiment"] / final_df["avg_price"]

# SAVE
final_df.to_csv("data/final_dataset.csv", index=False)

print("✅ final_dataset.csv ready")