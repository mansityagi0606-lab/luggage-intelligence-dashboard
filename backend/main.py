"""
main.py
FastAPI application — all routes for the luggage intelligence dashboard.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.db import store
from backend.models import (
    BrandSummary, BrandDetail, ProductOut, CompareResponse,
    InsightsResponse, OverviewStats,
)
from backend import insights as insights_module


# ── Lifespan: load data once at startup ──────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()
    yield


app = FastAPI(
    title="Luggage Intel API",
    description="Competitive intelligence dashboard API for luggage brands on Amazon India",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Overview ──────────────────────────────────────────────────────────────────

@app.get("/api/overview", response_model=OverviewStats, tags=["Overview"])
def get_overview():
    """
    High-level KPI snapshot:
    total brands, products, reviews, avg sentiment, best brand callouts.
    """
    return store.get_overview_stats()


# ── Brands ────────────────────────────────────────────────────────────────────

@app.get("/api/brands", response_model=list[BrandSummary], tags=["Brands"])
def get_all_brands():
    """
    List all brands with aggregated metrics.
    Sorted by avg_rating descending.
    """
    return store.get_all_brands()


@app.get("/api/brands/names", response_model=list[str], tags=["Brands"])
def get_brand_names():
    """Return just the list of brand names (for filter dropdowns)."""
    return store.get_brand_names()


@app.get("/api/brands/{brand_name}", response_model=BrandDetail, tags=["Brands"])
def get_brand_detail(brand_name: str):
    """
    Full brand detail: metrics + themes + all products.
    """
    brand = store.get_brand_detail(brand_name)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_name}' not found")
    return brand


# ── Products ──────────────────────────────────────────────────────────────────

@app.get("/api/products", tags=["Products"])
def get_products(
    brands: str | None = Query(None, description="Comma-separated brand names"),
    min_rating: float | None = Query(None, ge=1, le=5),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    size_tag: str | None = Query(None, enum=["cabin", "medium", "large", "set", "unknown"]),
    min_sentiment: float | None = Query(None, ge=-1, le=1),
    sort_by: str = Query("rating", enum=["rating", "price", "discount_pct", "sentiment_score", "review_count"]),
    order: str = Query("desc", enum=["asc", "desc"]),
):
    """
    Filtered + sorted product list. Reviews not included (use /products/{asin}).
    """
    brand_list = [b.strip() for b in brands.split(",")] if brands else None

    products = store.get_all_products(
        brands=brand_list,
        min_rating=min_rating,
        max_price=max_price,
        min_price=min_price,
        size_tag=size_tag,
        min_sentiment=min_sentiment,
    )

    # Sort
    reverse = order == "desc"
    products.sort(key=lambda p: (p.get(sort_by) or 0), reverse=reverse)

    return {"products": products, "total": len(products)}


@app.get("/api/products/{asin}", tags=["Products"])
def get_product(asin: str):
    """Full product detail including all reviews."""
    product = store.get_product(asin)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{asin}' not found")
    return product


# ── Comparison ────────────────────────────────────────────────────────────────

@app.get("/api/compare", response_model=CompareResponse, tags=["Compare"])
def compare_brands(
    brands: str = Query(..., description="Comma-separated brand names to compare"),
):
    """
    Side-by-side brand comparison.
    Returns the same structure as /brands but filtered to requested brands.
    """
    brand_list = [b.strip() for b in brands.split(",")]
    all_brands = store.get_all_brands()
    filtered = [b for b in all_brands if b["brand"] in brand_list]

    if not filtered:
        raise HTTPException(status_code=404, detail="None of the requested brands found")

    return {"brands": filtered}


# ── Agent Insights ────────────────────────────────────────────────────────────

@app.get("/api/insights", response_model=InsightsResponse, tags=["Insights"])
def get_insights(refresh: bool = Query(False, description="Force regenerate insights")):
    """
    5 non-obvious AI-generated competitive insights.
    Results are cached in memory — use ?refresh=true to regenerate.
    """
    if refresh:
        insights_module.clear_cache()

    all_brands = store.get_all_brands()
    return insights_module.generate_insights(all_brands)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "brands_loaded": len(store.db),
        "products_loaded": len(store.products_df),
    }