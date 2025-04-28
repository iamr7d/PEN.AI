import os
import time
import re
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import json
import logging
import argparse
import csv
from dotenv import load_dotenv

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def load_news(json_path='all_news.json'):
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_news(news_list, json_path='enhanced_news.json', csv_path='enhanced_news.csv'):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)
    # Save to CSV
    if news_list:
        keys = ['news_id', 'seo_headline', 'rewritten_summary', 'image_prompt', 'image_path', 'image_id', 'tags']
        with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            for item in news_list:
                row = {k: (', '.join(item.get(k, [])) if isinstance(item.get(k, []), list) else item.get(k, '')) for k in keys}
                writer.writerow(row)
    logging.info(f"Saved {len(news_list)} enhanced news articles to {json_path} and {csv_path}.")

from unique_id_util import generate_unique_id

def gemini_rewrite_and_image(news_item, gemini_api_key, unsplash_key, processed_ids=None):
    # Use existing news_id if present
    news_id = news_item.get('news_id') or generate_unique_id()
    if processed_ids and news_id in processed_ids:
        return None  # Already processed
    genai.configure(api_key=gemini_api_key)
    model_name = 'gemini-2.0-flash'
    print(f"[Gemini] Using model: {model_name}")
    text_model = genai.GenerativeModel(model_name)
    prompt = (
        f"Rewrite the following news headline and summary in the style of a senior BBC news editor or journalist: professional, objective, concise, and authoritative. Do NOT use emojis, smileys, or informal language. Headlines should be compelling but serious.\n"
        f"Original headline: {news_item.get('heading','')}\n"
        
        f"Original summary: {news_item.get('summary','')}\n"
        f"Return your answer as:\n"
        f"Headline: <headline>\nSummary: <summary>\n"
        f"Also, generate a prompt for an illustration image that matches the news."
    )
    import time
    import google.api_core.exceptions
    
    def call_with_retry(model, prompt, max_retries=5):
        delay = 30
        for attempt in range(max_retries):
            try:
                return model.generate_content(prompt)
            except google.api_core.exceptions.ResourceExhausted as e:
                if '429' in str(e) or 'quota' in str(e):
                    print(f"[Gemini] Quota exceeded, retrying in {delay} seconds (attempt {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                    delay = min(delay * 2, 300)
                else:
                    raise
        raise RuntimeError("Exceeded maximum retries due to Gemini API quota limits.")

    response = call_with_retry(text_model, prompt)

    lines = response.text.splitlines()
    headline, summary, image_prompt = "", "", ""
    for line in lines:
        if line.lower().startswith("headline:"):
            headline = line.partition(":")[2].strip()
        elif line.lower().startswith("summary:"):
            summary = line.partition(":")[2].strip()
        elif "illustration" in line.lower() or "image" in line.lower():
            image_prompt = line.partition(":")[2].strip()
    if not image_prompt:
        image_prompt = f"An illustration for: {headline or news_item.get('heading','')}"

    # Generate tags using Gemini
    tag_prompt = (
        f"Generate 5 relevant tags for this news article, separated by commas.\n"
        f"Headline: {headline or news_item.get('heading','')}\n"
        f"Summary: {summary or news_item.get('summary','')}"
    )
    tag_response = call_with_retry(text_model, tag_prompt)

    tags = [tag.strip() for tag in tag_response.text.split(',') if tag.strip()]

    # Use image_generator.py to generate and connect image, passing image_id and category bucket
    import subprocess
    import sys
    import json as pyjson
    image_id = news_id  # Use the same UUID for both news and image for strong linkage
    image_prompt_for_gen = image_prompt or headline or news_item.get('heading','')
    image_path = None
    result_path = None
    try:
        category = news_item.get('category', 'general')
        cmd = [
            'python', 'image_generator.py',
            '--prompt', f'{image_prompt_for_gen}',
            '--filename', news_id,
            '--gemini_key', gemini_api_key or '',
            '--unsplash_key', unsplash_key or '',
            '--category', category
        ]
        output = subprocess.check_output(cmd, universal_newlines=True)
        for line in output.splitlines():
            if line.startswith('Image saved to:'):
                result_path = line.split(':', 1)[1].strip()
    except Exception as e:
        print(f"Image generator subprocess failed: {e}")
    image_path = result_path

    return {
        'news_id': news_id,
        'seo_headline': headline or news_item.get('heading',''),
        'rewritten_summary': summary or news_item.get('summary',''),
        'image_prompt': image_prompt,
        'image_path': image_path,
        'image_id': image_id,
        'tags': tags,
    }

def deduplicate_news(news_list):
    seen = set()
    unique_news = []
    for news in news_list:
        # Use link or headline as deduplication key
        key = news.get('link') or news.get('heading')
        if key and key not in seen:
            seen.add(key)
            unique_news.append(news)
    return unique_news

def load_processed_ids(json_path='enhanced_news.json'):
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                return set(item['news_id'] for item in json.load(f) if 'news_id' in item)
            except Exception:
                return set()
    return set()

def main():
    setup_logging()
    load_dotenv()
    parser = argparse.ArgumentParser(description='Enhance news articles with Gemini and generate images.')
    parser.add_argument('--input', default='all_news.json', help='Input JSON file with aggregated news')
    parser.add_argument('--output', default='enhanced_news.json', help='Output JSON file for enhanced news')
    parser.add_argument('--csv', default='enhanced_news.csv', help='Output CSV file for enhanced news')
    parser.add_argument('--gemini_key', default=None, help='Gemini API key')
    parser.add_argument('--unsplash_key', default=None, help='Unsplash API key')
    parser.add_argument('--run_once', action='store_true', help='Run only once and exit')
    args = parser.parse_args()
    # Load from env if not provided as argument
    if not args.gemini_key:
        args.gemini_key = os.getenv('GEMINI_KEY')
    if not args.unsplash_key:
        args.unsplash_key = os.getenv('UNSPLASH_KEY')
    if not args.gemini_key or not args.unsplash_key:
        raise ValueError('Gemini and Unsplash API keys must be provided as arguments or in the .env file.')

    while True:
        all_news = load_news(args.input)
        all_news = deduplicate_news(all_news)
        processed_ids = load_processed_ids(args.output)
        enhanced_news = []
        for news_item in all_news:
            enhanced = gemini_rewrite_and_image(news_item, args.gemini_key, args.unsplash_key, processed_ids)
            if enhanced:
                enhanced_news.append(enhanced)
        # Merge with previously enhanced news
        if os.path.exists(args.output):
            with open(args.output, 'r', encoding='utf-8') as f:
                try:
                    prev = json.load(f)
                    enhanced_news = prev + enhanced_news
                except Exception:
                    pass
        save_news(enhanced_news, args.output, args.csv)
        logging.info(f"Enhanced {len(enhanced_news)} news articles.")
        if args.run_once:
            break
        time.sleep(3600)

if __name__ == "__main__":
    main()
