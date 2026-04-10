import pandas as pd

products = pd.read_csv("data/cleaned/combined_products.csv")
reviews = pd.read_csv("data/processed/reviews_with_sentiment.csv")

# --- Brand level metrics ---
brand_summary = products.groupby("brand").agg({
    "price": "mean",
    "discount_pct": "mean",
    "rating": "mean",
    "review_count": "sum"
}).reset_index()

# --- Sentiment score ---
sentiment_map = {"positive": 1, "neutral": 0, "negative": -1}
reviews["sentiment_score"] = reviews["sentiment"].map(sentiment_map)

# merge sentiment with brand
reviews["brand"] = reviews["product"].str.extract(r"(\w+)")

brand_sentiment = reviews.groupby("brand")["sentiment_score"].mean().reset_index()

# merge all
final = brand_summary.merge(brand_sentiment, on="brand", how="left")

final.to_csv("data/processed/brand_summary.csv", index=False)

print("✅ Brand analysis ready")