import feedparser
from newspaper import Article
from GoogleNews import GoogleNews
import pandas as pd
import json
import urllib.robotparser
import time
import logging
import argparse
from unique_id_util import generate_unique_id

# Optional: AI summarization
try:
    from transformers import pipeline
    summarizer = pipeline('summarization', model='facebook/bart-large-cnn')
except ImportError:
    summarizer = None
    print("[INFO] transformers not installed. AI summarization is disabled.")

# --- LEGAL & ETHICAL SAFEGUARDS ---
DISCLAIMER = (
    "This platform provides AI-generated news summaries for informational purposes only. "
    "Please visit the original source for the full article. All copyrights belong to the respective publishers. "
    "We respect robots.txt and Terms of Service of all sources."
)
print(DISCLAIMER)

# robots.txt checker
robots_cache = {}
def can_fetch(url, user_agent='*'):
    from urllib.parse import urlparse
    domain = urlparse(url).scheme + '://' + urlparse(url).netloc
    if domain not in robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(domain + '/robots.txt')
        try:
            rp.read()
            robots_cache[domain] = rp
        except Exception:
            robots_cache[domain] = None
    rp = robots_cache[domain]
    if rp:
        return rp.can_fetch(user_agent, url)
    return True  # If robots.txt can't be read, default to allow

# 1. RSS Feeds
rss_urls = [
    'http://feeds.bbci.co.uk/news/rss.xml',
    'https://rss.cnn.com/rss/edition.rss',
    'https://feeds.reuters.com/reuters/topNews',
    # Add more RSS feeds as needed
]

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def fetch_rss_news(rss_urls, max_per_feed=5, default_category='general'):
    news_list = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                # Try to extract category from entry, else use default_category
                category = None
                if 'tags' in entry and entry.tags:
                    category = entry.tags[0].term if hasattr(entry.tags[0], 'term') else entry.tags[0].get('term', default_category)
                elif 'category' in entry:
                    category = entry.category
                else:
                    category = default_category
                news_item = {
                    'news_id': generate_unique_id(),
                    'source': entry.get('source', {}).get('title', '') or entry.get('publisher', '') or url,
                    'heading': entry.title,
                    'summary': entry.summary if 'summary' in entry else '',
                    'link': entry.link,
                    'category': category
                }
                news_list.append(news_item)
        except Exception as e:
            logging.error(f"RSS error for {url}: {e}")
    return news_list

def fetch_google_news(topic='technology', max_results=5):
    news_list = []
    try:
        googlenews = GoogleNews(period='1d')
        googlenews.search(topic)
        for result in googlenews.results()[:max_results]:
            news_item = {
                'news_id': generate_unique_id(),
                'source': result.get('media', ''),
                'heading': result.get('title', ''),
                'summary': result.get('desc', ''),
                'link': result.get('link', ''),
                'category': topic
            }
            news_list.append(news_item)
    except Exception as e:
        logging.error(f"GoogleNews error: {e}")
    return news_list

def enrich_with_article_text(news_list, summarizer=None):
    for news in news_list:
        link = news.get('link', '')
        if link and can_fetch(link):
            try:
                article = Article(link)
                article.download()
                article.parse()
                news['full_text'] = article.text
                # AI summarization if available
                if summarizer and article.text:
                    try:
                        ai_summary = summarizer(article.text[:1024], max_length=60, min_length=20, do_sample=False)[0]['summary_text']
                        news['ai_summary'] = ai_summary
                    except Exception as e:
                        news['ai_summary'] = ''
                        logging.warning(f"Summarization failed: {e}")
                    time.sleep(1)  # avoid rate limits on HuggingFace pipeline
            except Exception as e:
                news['full_text'] = ''
                news['ai_summary'] = ''
                logging.warning(f"Article extraction failed for {link}: {e}")
        else:
            news['full_text'] = ''
            news['ai_summary'] = ''
    return news_list

def save_news(news_list, json_path='all_news.json', csv_path='all_news.csv'):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)
    pd.DataFrame(news_list).to_csv(csv_path, index=False, encoding='utf-8')
    logging.info(f"Aggregated {len(news_list)} news articles from multiple sources. Saved to {json_path} and {csv_path}.")

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Aggregate news from RSS and Google News.')
    parser.add_argument('--rss', nargs='+', default=[
        'http://feeds.bbci.co.uk/news/rss.xml',
        'https://rss.cnn.com/rss/edition.rss',
        'https://feeds.reuters.com/reuters/topNews'], help='List of RSS feed URLs')
    parser.add_argument('--topic', default='technology', help='Google News topic')
    parser.add_argument('--max_per_feed', type=int, default=5, help='Max articles per RSS feed')
    parser.add_argument('--max_google', type=int, default=5, help='Max Google News articles')
    parser.add_argument('--json_path', default='all_news.json', help='Output JSON path')
    parser.add_argument('--csv_path', default='all_news.csv', help='Output CSV path')
    args = parser.parse_args()

    rss_news = fetch_rss_news(args.rss, args.max_per_feed, default_category=args.topic)
    google_news = fetch_google_news(args.topic, args.max_google)
    all_news = rss_news + google_news

    # Process and save each news item one by one
    import os
    import csv
    # Group news by category
    from collections import defaultdict
    category_dict = defaultdict(list)
    for news in all_news:
        enriched = enrich_with_article_text([news], summarizer)[0]
        category = enriched.get('category', 'general')
        category_dict[category].append(enriched)

    # Write separate files for each category
    import re
    # Create 'news bucket' directory if it doesn't exist
    bucket_dir = os.path.join(os.getcwd(), 'news bucket')
    if not os.path.exists(bucket_dir):
        os.makedirs(bucket_dir)
    for category, items in category_dict.items():
        # Clean category name for filename
        safe_category = re.sub(r'[^A-Za-z0-9_\-]', '_', category.lower())
        json_path = os.path.join(bucket_dir, f'news_{safe_category}.json')
        csv_path = os.path.join(bucket_dir, f'news_{safe_category}.csv')
        # Write JSON as array (always a list)
        with open(json_path, 'w', encoding='utf-8') as f_json:
            f_json.write('[\n')
            for i, item in enumerate(items):
                json.dump(item, f_json, ensure_ascii=False, indent=2)
                if i < len(items) - 1:
                    f_json.write(',\n')
            f_json.write('\n]')
        # Write CSV
        if items:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f_csv:
                writer = csv.DictWriter(f_csv, fieldnames=items[0].keys())
                writer.writeheader()
                for item in items:
                    writer.writerow(item)
        logging.info(f"Saved {len(items)} articles to {json_path} and {csv_path}")

if __name__ == "__main__":
    main()
