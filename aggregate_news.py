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

def enrich_with_article_text(news_list):
    for news in news_list:
        link = news.get('link', '')
        if link and can_fetch(link):
            try:
                article = Article(link)
                article.download()
                article.parse()
                news['full_text'] = article.text
                if not news['full_text']:
                    logging.warning(f"[aggregate_news] Empty article text for {link}")
            except Exception as e:
                news['full_text'] = ''
                logging.warning(f"Article extraction failed for {link}: {e}")
        else:
            news['full_text'] = ''
    return news_list

def save_news(news_list, json_path='all_news.json', csv_path='all_news.csv'):
    import os
    import json
    import pandas as pd
    # Load existing news if present
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_news = json.load(f)
        except Exception:
            existing_news = []
    else:
        existing_news = []
    # Merge and deduplicate by news_id
    all_news = {item['news_id']: item for item in existing_news if 'news_id' in item}
    for item in news_list:
        if 'news_id' in item:
            all_news[item['news_id']] = item
    merged_news = list(all_news.values())
    # Save merged news
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(merged_news, f, ensure_ascii=False, indent=2)
    pd.DataFrame(merged_news).to_csv(csv_path, index=False, encoding='utf-8')
    logging.info(f"Aggregated {len(news_list)} new articles, {len(merged_news)} total. Saved to {json_path} and {csv_path}.")

def main():
    setup_logging()
    # Load .env if present
    import os
    from dotenv import load_dotenv
    load_dotenv()
    default_gemini_key = os.getenv('GEMINI_KEY') or os.getenv('GEMINI_API_KEY')
    default_unsplash_key = os.getenv('UNSPLASH_KEY') or os.getenv('UNSPLASH_ACCESS_KEY')
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
    parser.add_argument('--gemini_enhance', action='store_true', help='Run Gemini enhancer on each category after aggregation')
    parser.add_argument('--gemini_key', type=str, default=default_gemini_key, help='Gemini API key (optional)')
    parser.add_argument('--unsplash_key', type=str, default=default_unsplash_key, help='Unsplash API key (optional)')
    args = parser.parse_args()

    # Fetch news
    rss_news = fetch_rss_news(args.rss, args.max_per_feed)
    google_news = fetch_google_news(args.topic, args.max_google)
    all_news = rss_news + google_news
    all_news = enrich_with_article_text(all_news)

    # Force output to all_news.json and all_news.csv at project root
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'all_news.json'))
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'all_news.csv'))
    save_news(all_news, json_path=json_path, csv_path=csv_path)

    rss_news = fetch_rss_news(args.rss, args.max_per_feed, default_category=args.topic)
    google_news = fetch_google_news(args.topic, args.max_google)
    all_news = rss_news + google_news

    # Process and save each news item one by one
    import os
    import csv
    from collections import defaultdict
    import re
    import subprocess
    category_dict = defaultdict(list)
    for news in all_news:
        enriched = enrich_with_article_text([news])[0]
        category = enriched.get('category', 'general')
        category_dict[category].append(enriched)

    # Create 'news bucket' directory if it doesn't exist
    bucket_dir = os.path.join(os.getcwd(), 'news bucket')
    if not os.path.exists(bucket_dir):
        os.makedirs(bucket_dir)
    for category, items in category_dict.items():
        # Clean category name for filename
        safe_category = re.sub(r'[^A-Za-z0-9_\-]', '_', category.lower())
        json_path = os.path.join(bucket_dir, f'news_{safe_category}.json')
        csv_path = os.path.join(bucket_dir, f'news_{safe_category}.csv')
        save_news(items, json_path, csv_path)
        # Optionally run Gemini enhancer
        if args.gemini_enhance:
            gemini_args = [
                'python', 'gemini_news_enhancer.py',
                '--news_json', json_path,
                '--output_json', os.path.join(bucket_dir, f'news_{safe_category}_gemini.json'),
                '--output_csv', os.path.join(bucket_dir, f'news_{safe_category}_gemini.csv')
            ]
            if args.gemini_key:
                gemini_args += ['--gemini_key', args.gemini_key]
            if args.unsplash_key:
                gemini_args += ['--unsplash_key', args.unsplash_key]
            logging.info(f"Running Gemini enhancer for {json_path} ...")
            try:
                subprocess.run(gemini_args, check=True)
            except Exception as e:
                logging.error(f"Gemini enhancer failed for {json_path}: {e}")

if __name__ == "__main__":
    main()
