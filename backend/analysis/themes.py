import pandas as pd
from collections import Counter
import re

# Basic stopwords (can expand later)
stopwords = set([
    "the", "and", "for", "this", "that", "with", "was", "are", "but",
    "very", "have", "has", "had", "you", "your", "they", "them",
    "from", "will", "would", "should", "can", "could", "about",
    "there", "their", "what", "when", "where", "which", "who",
    "is", "am", "be", "been", "being", "to", "of", "in", "on",
    "it", "as", "at", "by", "an", "or"
])

df = pd.read_csv("data/processed/reviews_with_sentiment.csv")

words = []

for review in df["review"].dropna():
    # Clean text
    review = review.lower()
    review = re.sub(r'[^a-z\s]', '', review)

    for word in review.split():
        if word not in stopwords and len(word) > 3:
            words.append(word)

# Count meaningful words
common = Counter(words).most_common(20)

themes = pd.DataFrame(common, columns=["word", "count"])
themes.to_csv("data/processed/themes.csv", index=False)

print("✅ Clean themes generated")