import requests
import os
import logging
import argparse
from unique_id_util import generate_unique_id

def fetch_latest_news(api_key, country='us', page_size=10):
    url = 'https://newsapi.org/v2/top-headlines'
    params = {
        'apiKey': api_key,
        'country': country,
        'pageSize': page_size
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        news_data = response.json()
        articles = news_data.get('articles', [])
        if not articles:
            print('No news articles found.')
            return
        print(f"Latest News Headlines ({country.upper()}):\n")
        news_list = []
        for idx, article in enumerate(articles, 1):
            source = article.get('source', {}).get('name')
            heading = article.get('title')
            def clean_heading(heading, source):
                if not heading or not source:
                    return heading
                patterns = [source]
                abbreviations = {
                    'The Wall Street Journal': ['WSJ'],
                    'Associated Press': ['AP News'],
                    'NBCSports.com': ['NBC Sports'],
                    'Reuters': ['Reuters'],
                    'CNN': ['CNN'],
                    'ABC News': ['ABC News'],
                }
                for k, v in abbreviations.items():
                    if source == k:
                        patterns.extend(v)
                for pat in patterns:
                    if heading.strip().endswith(f'- {pat}'):
                        return heading[:-(len(pat) + 2)].strip()
                return heading
            heading = clean_heading(heading, source)
            description = article.get('description')
            content = article.get('content')
            summary_parts = []
            if description:
                summary_parts.append(description.strip())
            if content:
                summary_parts.append(content.strip())
            summary = ' '.join(summary_parts)
            link = article.get('url')
            news_list.append({
                'news_id': generate_unique_id(),
                'source': source,
                'heading': heading,
                'summary': summary,
                'link': link
            })
            logging.info(f"{idx}. {heading}")
            logging.info(f"   Source: {source}")
            if summary:
                logging.info(f"   Summary: {summary}")
        import json
        with open('news.json', 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        logging.info(f"Saved {len(news_list)} news articles to news.json.")
    else:
        print(f"Failed to fetch news: {response.status_code}")

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Fetch latest news using NewsAPI.')
    parser.add_argument('--api_key', required=True, help='NewsAPI API key')
    parser.add_argument('--country', default='us', help='Country code')
    parser.add_argument('--page_size', type=int, default=10, help='Number of articles to fetch')
    parser.add_argument('--output', default='news.json', help='Output JSON file')
    args = parser.parse_args()
    fetch_latest_news(args.api_key, args.country, args.page_size)

if __name__ == "__main__":
    main()
