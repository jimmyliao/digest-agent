
import asyncio
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import desc
from src.orchestrator import DigestOrchestrator
from src.models.database import SessionLocal, ArticleDB

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("publish_latest")

async def main():
    orchestrator = DigestOrchestrator()
    db = SessionLocal()
    
    # 1. Select the 3 latest articles from the DB
    latest_articles = db.query(ArticleDB).order_by(desc(ArticleDB.created_at)).limit(3).all()
    
    if not latest_articles:
        logger.warning("No articles found in DB.")
        db.close()
        return

    logger.info(f"Found {len(latest_articles)} articles. Processing summaries...")

    # 2. Summarize the articles (as they are likely not summarized yet)
    # Each article needs title and content
    articles_data = [{"title": a.title, "content": a.content} for a in latest_articles]
    summaries = await orchestrator.summarizer.summarize_batch(articles_data)
    
    publish_data = []
    for i, a in enumerate(latest_articles):
        summary_res = summaries[i]
        
        # Save summary back to DB if needed
        if summary_res and not (summary_res.raw_response and summary_res.raw_response.startswith("ERROR:")):
            # Prepare data for publishing
            publish_data.append({
                "id": a.id,
                "title": summary_res.title_zh or a.title,
                "summary": summary_res.summary_zh or "",
                "url": a.source_url,
                "source": a.source,
                "tags": summary_res.tags or [],
                "key_points": summary_res.key_points or []
            })
            
            # Update DB record with summary (stored in 'summary' field as JSON)
            a.summary = json.dumps({
                "title_zh": summary_res.title_zh,
                "summary_zh": summary_res.summary_zh,
                "key_points": summary_res.key_points,
                "tags": summary_res.tags
            })
            a.publish_status = "summarized"
            a.summarized_at = datetime.now(timezone.utc)
            db.add(a)

    db.commit()
    db.close()

    if not publish_data:
        logger.error("No summaries generated successfully.")
        return

    # 3. Publish to Telegram
    logger.info(f"Publishing {len(publish_data)} articles to Telegram...")
    publish_res = await orchestrator.run_publish_pipeline(articles=publish_data, channels=["telegram"])
    
    if publish_res.success:
        logger.info("Successfully published latest 3 articles to Telegram.")
    else:
        logger.error(f"Publish failed: {publish_res.errors}")

if __name__ == "__main__":
    asyncio.run(main())
