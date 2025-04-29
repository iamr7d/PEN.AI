import os
import time
import re
try:
    from google import genai
    _GENAI_CLIENT_STYLE = True
except ImportError:
    import google.generativeai as genai
    _GENAI_CLIENT_STYLE = hasattr(genai, "Client")

from PIL import Image
from io import BytesIO
import json
import logging
import argparse
import csv
from dotenv import load_dotenv
from parse_gemini_response import parse_gemini_response

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def load_news(json_path='all_news.json'):
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logging.warning(f"{json_path} is empty. Returning empty list.")
                    return []
                return json.loads(content)
        except Exception as e:
            logging.warning(f"Failed to load or parse {json_path}: {e}. Returning empty list.")
            return []
    return []

import shutil

def save_news(news_list, json_path='enhanced_news.json', csv_path='enhanced_news.csv'):
    import os
    import shutil
    import requests
    images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'images'))
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    for news in news_list:
        image_set = False
        if 'image_path' in news and news['image_path']:
            img_path = news['image_path']
            if img_path.startswith('http://') or img_path.startswith('https://'):
                # Download image
                try:
                    img_filename = os.path.basename(img_path.split('?')[0])
                    local_img_path = os.path.join(images_dir, img_filename)
                    if not os.path.exists(local_img_path):
                        response = requests.get(img_path, timeout=10)
                        if response.status_code == 200:
                            with open(local_img_path, 'wb') as f:
                                f.write(response.content)
                            logging.info(f"Downloaded image for news {news.get('news_id', '')} to {local_img_path}")
                        else:
                            raise Exception(f"HTTP {response.status_code}")
                    news['image'] = img_filename
                    image_set = True
                except Exception as e:
                    logging.warning(f"Failed to download image for news {news.get('news_id', '')}: {e}")
            else:
                # Local file, copy if not in images_dir
                try:
                    img_filename = os.path.basename(img_path)
                    local_img_path = os.path.join(images_dir, img_filename)
                    if not os.path.exists(local_img_path) and os.path.exists(img_path):
                        shutil.copyfile(img_path, local_img_path)
                        logging.info(f"Copied image for news {news.get('news_id', '')} to {local_img_path}")
                    news['image'] = img_filename
                    image_set = True
                except Exception as e:
                    logging.warning(f"Failed to copy image for news {news.get('news_id', '')}: {e}")
        if not image_set:
            if 'image_id' in news and news['image_id']:
                news['image'] = f"{news['image_id']}.jpg"
            else:
                news['image'] = 'no-image.png'
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
    # AUTOMATION: Copy enhanced_news.json to news bucket
    news_bucket_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'news bucket', 'enhanced_news.json'))
    try:
        shutil.copyfile(json_path, news_bucket_path)
        logging.info(f"Copied {json_path} to {news_bucket_path} for backend consumption.")
    except Exception as e:
        logging.error(f"Failed to copy enhanced news to news bucket: {e}")

from unique_id_util import generate_unique_id

def gemini_rewrite_and_image(news_item, gemini_api_key, unsplash_key, processed_ids=None):
    # Use existing news_id if present
    headline, summary, image_prompt = "", "", ""
    for line in lines:
        if line.lower().startswith("headline:"):
            headline = line.partition(":")[2].strip()
        elif line.lower().startswith("summary:"):
            summary = line.partition(":")[2].strip()
        elif "illustration" in line.lower() or "image" in line.lower():
            image_prompt = line.partition(":")[2].strip()
    if not image_prompt:
        image_prompt = f"An illustration for: {headline}"
    return {'seo_headline': headline, 'rewritten_summary': summary, 'image_prompt': image_prompt}

def call_with_retry(client, model_name, prompt, max_retries=5):
    delay = 30
    for attempt in range(max_retries):
        try:
            if _GENAI_CLIENT_STYLE:
                return client.models.generate_content(model=model_name, contents=prompt)
            else:
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                model = genai.GenerativeModel(model_name)
                return model.generate_content(prompt)
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e):
                print(f"[Gemini] Quota exceeded, retrying in {delay} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
                delay = min(delay * 2, 300)
            else:
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
    raise RuntimeError("Exceeded maximum retries due to Gemini API quota limits.")

def gemini_rewrite_and_image(news_item, gemini_api_key, unsplash_key, processed_ids=None):
    # Use existing news_id if present
    news_id = news_item.get('news_id') or generate_unique_id()
    if processed_ids and news_id in processed_ids:
        return None  # Already processed
    model_name = 'gemini-2.0-flash'
    print(f"[Gemini] Using model: {model_name}")
    client = genai.Client(api_key=gemini_api_key or os.getenv("GOOGLE_API_KEY")) if _GENAI_CLIENT_STYLE else None
    try:
        prompt = (
            f"Rewrite the following news article in the style of a senior BBC news editor or journalist. "
            f"Your output should be:\n"
            f"Headline: <headline>\n"
            f"Summary: <3 paragraphs summarizing the full article, professional, objective, concise, and authoritative. No emojis or informal language.>\n"
            f"Full Article: <Rewrite the entire article in 4-8 paragraphs, professional, objective, and detailed. No emojis or informal language.>\n"
            f"Also, generate a prompt for an illustration image that matches the news.\n"
            f"Original headline: {news_item.get('heading','')}\n"
            f"Full article: {news_item.get('full_text', news_item.get('summary',''))}\n"
        )
        response = call_with_retry(client, model_name, prompt)
        rewritten = parse_gemini_response(response.text)
        # Ensure rewritten_full_text is present
        if 'rewritten_full_text' not in rewritten:
            rewritten['rewritten_full_text'] = ''
        # Generate a highly relevant image prompt using the full rewritten article
        image_prompt_context = (
            f"Given the following news article, generate a highly descriptive prompt for an illustration image that best represents the story. "
            f"Be specific, avoid generic phrases, and focus on the key people, places, events, and mood.\n"
            f"Article: {rewritten['rewritten_full_text'] or news_item.get('full_text', news_item.get('summary',''))}"
        )
        try:
            improved_image_prompt_resp = call_with_retry(client, model_name, image_prompt_context)
            improved_image_prompt = improved_image_prompt_resp.text.strip()
            if improved_image_prompt:
                rewritten['image_prompt'] = improved_image_prompt
        except Exception as e:
            logging.warning(f"Gemini image prompt improvement failed for news_id {news_id}: {e}")
    except Exception as e:
        logging.warning(f"Gemini rewrite failed for news_id {news_id}: {e}")
        rewritten = {'seo_headline': '', 'rewritten_summary': '', 'image_prompt': ''}
    # Generate tags using Gemini
    tag_prompt = (
        f"Generate 5 relevant tags for this news article, separated by commas.\n"
        f"Headline: {rewritten['seo_headline'] or news_item.get('heading','')}\n"
        f"Summary: {rewritten['rewritten_summary'] or news_item.get('summary','')}"
    )
    try:
        tag_response = call_with_retry(client, model_name, tag_prompt)
        tags = [tag.strip() for tag in tag_response.text.split(',') if tag.strip()]
    except Exception as e:
        logging.warning(f"Gemini tag generation failed for news_id {news_id}: {e}")
        tags = []
    # Use image_generator.py to generate and connect image, passing image_id and category bucket
    import subprocess
    import sys
    import json as pyjson
    image_id = news_id  # Use the same UUID for both news and image for strong linkage
    image_prompt_for_gen = rewritten['image_prompt'] or rewritten['seo_headline'] or news_item.get('heading','')
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
        'seo_headline': rewritten['seo_headline'] or news_item.get('heading',''),
        'rewritten_summary': rewritten['rewritten_summary'] or news_item.get('summary',''),
        'rewritten_full_text': rewritten.get('rewritten_full_text', ''),
        'image_prompt': rewritten['image_prompt'],
        'image_path': os.path.basename(image_path) if image_path else None,
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

def batch_gemini_rewrite(input_json, output_json, gemini_api_key, unsplash_key=None):
    setup_logging()
    news_list = load_news(input_json)
    enhanced_news = []
    for i, item in enumerate(news_list):
        result = gemini_rewrite_and_image(item, gemini_api_key, unsplash_key)
        if result:
            # Preserve all original fields and add/overwrite rewritten fields
            item.update({
                'seo_headline': result.get('seo_headline'),
                'rewritten_summary': result.get('rewritten_summary'),
                'image_prompt': result.get('image_prompt'),
                'image_path': result.get('image_path'),
                'image_id': result.get('image_id'),
                'tags': result.get('tags'),
            })
            enhanced_news.append(item)
        if (i+1) % 5 == 0:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(enhanced_news, f, ensure_ascii=False, indent=2)
            logging.info(f"Checkpoint: processed {i+1} articles.")
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(enhanced_news, f, ensure_ascii=False, indent=2)
    logging.info(f"Completed enhancing {len(enhanced_news)} news articles.")

def main():
    parser = argparse.ArgumentParser(description='Enhance news articles with Gemini AI.')
    parser.add_argument('--news_json', type=str, default='all_news.json', help='Path to input news JSON')
    parser.add_argument('--output_json', type=str, default='enhanced_news.json', help='Path to output enhanced news JSON')
    parser.add_argument('--output_csv', type=str, default='enhanced_news.csv', help='Path to output enhanced news CSV')
    parser.add_argument('--gemini_key', type=str, default=None, help='Gemini API key')
    parser.add_argument('--unsplash_key', type=str, default=None, help='Unsplash API key')
    parser.add_argument('--skip_existing', action='store_true', help='Skip already processed news_id')
    parser.add_argument('--batch_rewrite', action='store_true', help='Batch rewrite all articles in input JSON and save to output JSON')
    args = parser.parse_args()

    if args.batch_rewrite:
        gemini_api_key = args.gemini_key or os.getenv('GEMINI_API_KEY')
        unsplash_key = args.unsplash_key or os.getenv('UNSPLASH_ACCESS_KEY')
        batch_gemini_rewrite(args.news_json, args.output_json, gemini_api_key, unsplash_key)
        return

    setup_logging()
    load_dotenv()
    gemini_api_key = args.gemini_key or os.getenv('GEMINI_API_KEY')
    unsplash_key = args.unsplash_key or os.getenv('UNSPLASH_ACCESS_KEY')

    news_list = load_news(args.news_json)
    processed_ids = set()
    if args.skip_existing:
        processed_ids = set(load_processed_ids(args.output_json))

    enhanced_news = []
    for i, item in enumerate(news_list):
        if args.skip_existing and item.get('news_id') in processed_ids:
            continue
        result = gemini_rewrite_and_image(item, gemini_api_key, unsplash_key, processed_ids)
        if result:
            enhanced_news.append(result)
        if (i+1) % 5 == 0:
            save_news(enhanced_news, args.output_json, args.output_csv)
            logging.info(f"Checkpoint: processed {i+1} articles.")
    save_news(enhanced_news, args.output_json, args.output_csv)
    logging.info(f"Completed enhancing {len(enhanced_news)} news articles.")

if __name__ == "__main__":
    main()
