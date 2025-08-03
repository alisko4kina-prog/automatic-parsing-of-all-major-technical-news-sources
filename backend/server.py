from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
import re
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Tech News Aggregator", version="1.0.0")
api_router = APIRouter(prefix="/api")

# RSS Sources Configuration
RSS_SOURCES = {
    "techcrunch": {
        "url": "https://techcrunch.com/feed/",
        "name": "TechCrunch",
        "category": "technology",
        "color": "#00D084"
    },
    "theverge": {
        "url": "https://www.theverge.com/rss/index.xml",
        "name": "The Verge",
        "category": "technology",
        "color": "#FF6600"
    },
    "arstechnica": {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "name": "Ars Technica",
        "category": "technology",
        "color": "#FF4500"
    },
    "wired": {
        "url": "https://www.wired.com/feed/rss",
        "name": "Wired",
        "category": "technology",
        "color": "#000000"
    },
    "hackernews": {
        "url": "https://hnrss.org/frontpage",
        "name": "Hacker News",
        "category": "technology",
        "color": "#FF6600"
    }
}

# Models
class Article(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    summary: str
    content: str = ""
    url: str
    image_url: Optional[str] = None
    source: str
    source_name: str
    source_color: str
    category: str
    published_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)

class ArticleResponse(BaseModel):
    articles: List[Article]
    total: int
    page: int
    per_page: int

# Utility functions
def clean_html(raw_html):
    """Clean HTML tags and extract plain text"""
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

def extract_image_from_content(content, entry):
    """Extract first image from content or entry"""
    try:
        # Try to get image from entry media
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0].get('url', '')
        
        # Try to get image from enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type and enclosure.type.startswith('image/'):
                    return enclosure.href
        
        # Try to extract from content using BeautifulSoup
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            img_tag = soup.find('img')
            if img_tag and img_tag.get('src'):
                return img_tag.get('src')
    except Exception as e:
        logger.error(f"Error extracting image: {e}")
    
    return None

def extract_tags_from_content(title, content):
    """Extract relevant tags from title and content"""
    tech_keywords = [
        'AI', 'artificial intelligence', 'machine learning', 'blockchain',
        'cryptocurrency', 'bitcoin', 'ethereum', 'startup', 'venture capital',
        'google', 'apple', 'microsoft', 'amazon', 'meta', 'tesla', 'openai',
        'cybersecurity', 'data', 'cloud', 'mobile', 'app', 'software',
        'hardware', 'gaming', 'vr', 'ar', 'iot', 'robotics', 'drone'
    ]
    
    text = f"{title} {content}".lower()
    found_tags = []
    
    for keyword in tech_keywords:
        if keyword.lower() in text:
            found_tags.append(keyword.title())
    
    return found_tags[:5]  # Limit to 5 tags

async def fetch_rss_feed(source_key, source_config):
    """Fetch and parse RSS feed for a source"""
    try:
        logger.info(f"Fetching RSS feed for {source_config['name']}")
        
        # Add headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(source_config['url'], headers=headers, timeout=30)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        articles = []
        
        if not feed.entries:
            logger.warning(f"No entries found for {source_config['name']}")
            return []
        
        for entry in feed.entries[:10]:  # Limit to 10 latest articles per source
            try:
                # Extract content
                content = ""
                if hasattr(entry, 'content') and entry.content:
                    content = entry.content[0].value if isinstance(entry.content, list) else entry.content
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                
                content_text = clean_html(content)
                summary = entry.summary if hasattr(entry, 'summary') else content_text[:200] + "..."
                
                # Extract image
                image_url = extract_image_from_content(content, entry)
                
                # Parse published date
                published_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_date = datetime(*entry.updated_parsed[:6])
                
                # Extract tags
                tags = extract_tags_from_content(entry.title, content_text)
                
                article = Article(
                    title=entry.title,
                    summary=clean_html(summary)[:500] + "..." if len(clean_html(summary)) > 500 else clean_html(summary),
                    content=content_text[:1000] + "..." if len(content_text) > 1000 else content_text,
                    url=entry.link,
                    image_url=image_url,
                    source=source_key,
                    source_name=source_config['name'],
                    source_color=source_config['color'],
                    category=source_config['category'],
                    published_date=published_date,
                    tags=tags
                )
                
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Error processing entry from {source_config['name']}: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(articles)} articles from {source_config['name']}")
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching RSS feed for {source_config['name']}: {e}")
        return []

async def update_all_feeds():
    """Update all RSS feeds"""
    logger.info("Starting RSS feed update cycle")
    
    all_articles = []
    for source_key, source_config in RSS_SOURCES.items():
        articles = await fetch_rss_feed(source_key, source_config)
        all_articles.extend(articles)
    
    # Store articles in database (avoid duplicates by URL)
    for article in all_articles:
        try:
            existing = await db.articles.find_one({"url": article.url})
            if not existing:
                await db.articles.insert_one(article.dict())
                logger.info(f"Inserted new article: {article.title[:50]}...")
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
    
    logger.info(f"RSS feed update completed. Processed {len(all_articles)} articles")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Tech News Aggregator API"}

@api_router.get("/articles", response_model=ArticleResponse)
async def get_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    hours: Optional[int] = Query(None, ge=1, le=168)  # Filter by hours (max 1 week)
):
    """Get articles with filtering and pagination"""
    try:
        # Build query
        query = {}
        
        if source:
            query["source"] = source
        
        if category:
            query["category"] = category
            
        if hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            query["published_date"] = {"$gte": cutoff_time}
        
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"summary": {"$regex": search, "$options": "i"}},
                {"tags": {"$in": [search]}}
            ]
        
        # Get total count
        total = await db.articles.count_documents(query)
        
        # Get articles with pagination
        skip = (page - 1) * per_page
        cursor = db.articles.find(query).sort("published_date", -1).skip(skip).limit(per_page)
        articles_data = await cursor.to_list(length=per_page)
        
        articles = [Article(**article) for article in articles_data]
        
        return ArticleResponse(
            articles=articles,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch articles")

@api_router.get("/sources")
async def get_sources():
    """Get all available sources"""
    sources = []
    for key, config in RSS_SOURCES.items():
        # Get article count for each source
        count = await db.articles.count_documents({"source": key})
        sources.append({
            "key": key,
            "name": config["name"],
            "category": config["category"],
            "color": config["color"],
            "article_count": count
        })
    return {"sources": sources}

@api_router.get("/stats")
async def get_stats():
    """Get aggregator statistics"""
    try:
        total_articles = await db.articles.count_documents({})
        
        # Articles by source
        pipeline = [
            {"$group": {"_id": "$source_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        by_source = await db.articles.aggregate(pipeline).to_list(length=None)
        
        # Recent articles (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_count = await db.articles.count_documents({"published_date": {"$gte": cutoff_time}})
        
        return {
            "total_articles": total_articles,
            "recent_articles_24h": recent_count,
            "by_source": by_source,
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")

@api_router.post("/refresh")
async def manual_refresh():
    """Manually trigger RSS feed refresh"""
    try:
        await update_all_feeds()
        return {"message": "Feed refresh completed successfully"}
    except Exception as e:
        logger.error(f"Error during manual refresh: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh feeds")

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scheduler for periodic RSS updates
scheduler = AsyncIOScheduler(timezone=pytz.utc)

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("Starting Tech News Aggregator...")
    
    # Create database indexes
    await db.articles.create_index("url", unique=True)
    await db.articles.create_index([("published_date", -1)])
    await db.articles.create_index("source")
    
    # Initial feed fetch
    await update_all_feeds()
    
    # Schedule periodic updates (every 30 minutes)
    scheduler.add_job(
        update_all_feeds,
        'interval',
        minutes=30,
        id='rss_update',
        replace_existing=True
    )
    scheduler.start()
    logger.info("RSS update scheduler started (30-minute intervals)")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    client.close()
    logger.info("Application shutdown complete")