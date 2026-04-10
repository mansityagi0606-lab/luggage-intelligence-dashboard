import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Luggage Intelligence Dashboard", layout="wide")

# ==============================
# LOAD DATA
# ==============================

@st.cache_data
def load_data():
    products = pd.read_csv("data/cleaned/combined_products.csv")
    reviews = pd.read_csv("data/processed/reviews_with_sentiment.csv")
    brand_summary = pd.read_csv("data/processed/brand_summary.csv")
    themes = pd.read_csv("data/processed/themes.csv")
    return products, reviews, brand_summary, themes

products, reviews, brand_summary, themes = load_data()

# ==============================
# SIDEBAR FILTERS
# ==============================

st.sidebar.header("🔍 Filters")

price_range = st.sidebar.slider(
    "Price Range",
    int(products["price"].min()),
    int(products["price"].max()),
    (int(products["price"].min()), int(products["price"].max()))
)

selected_brands = st.sidebar.multiselect(
    "Select Brands",
    options=products["brand"].unique(),
    default=products["brand"].unique()
)

# Apply filters
products = products[
    (products["price"] >= price_range[0]) &
    (products["price"] <= price_range[1]) &
    (products["brand"].isin(selected_brands))
]

brand_summary = brand_summary[
    brand_summary["brand"].isin(selected_brands)
]

# ==============================
# TITLE
# ==============================

st.title("🧳 Luggage Competitive Intelligence Dashboard")

# ==============================
# KPIs
# ==============================

col1, col2, col3 = st.columns(3)

col1.metric("Total Products", len(products))
col2.metric("Avg Price", f"₹{int(products['price'].mean())}")
col3.metric("Avg Rating", round(products["rating"].mean(), 2))

# ==============================
# 🏆 AWARDS
# ==============================

st.subheader("🏆 Market Leaders")

best_brand = brand_summary.sort_values("sentiment_score", ascending=False).iloc[0]
best_value = brand_summary.sort_values("price").iloc[0]

col1, col2 = st.columns(2)
col1.success(f"🥇 Best Brand: {best_brand['brand']}")
col2.info(f"💰 Best Value: {best_value['brand']}")

# ==============================
# BRAND COMPARISON TABLE
# ==============================

st.subheader("📊 Brand Comparison")

st.dataframe(
    brand_summary.sort_values("sentiment_score", ascending=False),
    use_container_width=True
)

# ==============================
# 💰 PRICE VS SENTIMENT (INTERACTIVE)
# ==============================

st.subheader("💰 Price vs Sentiment")

fig1 = px.scatter(
    brand_summary,
    x="price",
    y="sentiment_score",
    color="brand",
    size="review_count",
    hover_data=["rating"],
    title="Price vs Sentiment Analysis"
)

st.plotly_chart(fig1, use_container_width=True)

# ==============================
# 🏷️ DISCOUNT STRATEGY
# ==============================

st.subheader("🏷️ Discount Strategy")

fig2 = px.bar(
    brand_summary,
    x="brand",
    y="discount_pct",
    color="brand",
    title="Discount Percentage by Brand"
)

st.plotly_chart(fig2, use_container_width=True)

# ==============================
# ⭐ TOP PRODUCTS
# ==============================

st.subheader("⭐ Top Rated Products")

top_products = products.sort_values(by="rating", ascending=False).head(10)

st.dataframe(top_products, use_container_width=True)

# ==============================
# 🧠 REVIEW THEMES
# ==============================

st.subheader("🧠 Common Review Themes")

fig3 = px.bar(
    themes.head(10),
    x="word",
    y="count",
    title="Top Words in Reviews"
)

st.plotly_chart(fig3, use_container_width=True)

# ==============================
# 📝 REVIEWS TABLE
# ==============================

st.subheader("📝 Sample Customer Reviews")

st.dataframe(reviews.head(50), use_container_width=True)

# ==============================
# 🤖 BUSINESS INSIGHTS
# ==============================

st.subheader("🤖 AI Business Recommendations")

for _, row in brand_summary.iterrows():
    if row["sentiment_score"] < 0:
        st.warning(f"{row['brand']} → Improve product quality & customer satisfaction")
    elif row["discount_pct"] > 40:
        st.info(f"{row['brand']} → High dependency on discounts for sales")
    else:
        st.success(f"{row['brand']} → Strong brand positioning and customer perception")

# ==============================
# 📌 FINAL INSIGHTS SUMMARY
# ==============================

st.subheader("📌 Key Insights Summary")

st.markdown("""
- Mid-priced brands often outperform premium brands in customer sentiment  
- High discounts may signal weak product perception  
- Durability and wheels are common customer concerns  
- Value-for-money brands dominate the market  
- Ratings alone can be misleading — sentiment analysis reveals deeper insights  
""")