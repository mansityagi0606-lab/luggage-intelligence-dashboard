import os
import pandas as pd
from textblob import TextBlob

# Create folder if not exists
os.makedirs("data/processed", exist_ok=True)

df = pd.read_csv("data/cleaned/generated_reviews.csv")

def get_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0:
        return "positive"
    elif polarity < 0:
        return "negative"
    else:
        return "neutral"

df["sentiment"] = df["review"].apply(get_sentiment)

df.to_csv("data/processed/reviews_with_sentiment.csv", index=False)

print("✅ Sentiment analysis completed")