# Planet Earth News (PEN) - AI-Driven News Aggregation Platform

## Overview
PEN is an AI-powered news platform that aggregates news from multiple sources, enhances headlines and summaries using Google Gemini, generates tags, and creates SEO-friendly images for each article. Each news article and image is linked via a unique UUID for robust data management.

## Features
- Aggregates news from RSS feeds, Google News, and NewsAPI.
- Assigns a unique UUID (`news_id`) to every news article and (`image_id`) to every image.
- Enhances headlines and summaries with Gemini AI.
- Generates relevant tags for each article.
- Automates image generation using Gemini API, with Unsplash fallback.
- All outputs are saved in both JSON and CSV formats, with consistent fields.
- Modular, robust, and easily extensible codebase.

## Usage

### 1. Aggregate News
```
python aggregate_news.py --rss <rss_url1> <rss_url2> ... --topic <google_news_topic> --max_per_feed <N> --max_google <N>
```
- Outputs: `all_news.json`, `all_news.csv`

### 2. Fetch Latest News from NewsAPI
```
python latest_news.py --api_key <YOUR_NEWSAPI_KEY> --country <country_code> --page_size <N> --output <output_file.json>
```
- Outputs: `news.json` (or specified output file)

### 3. Enhance News & Generate Images
```
python gemini_news_enhancer.py --gemini_key <YOUR_GEMINI_KEY> --unsplash_key <YOUR_UNSPLASH_KEY> --input all_news.json --output enhanced_news.json --csv enhanced_news.csv --run_once
```
- Only new/unprocessed news are enhanced each run.
- Outputs: `enhanced_news.json`, `enhanced_news.csv`

### 4. Generate Images Directly
```
python image_generator.py --prompt "A futuristic city skyline at sunset" --filename <unique_id> --gemini_key <YOUR_GEMINI_KEY> --unsplash_key <YOUR_UNSPLASH_KEY>
```
- Outputs: Image file in `images/` directory, prints image path and image_id.

## Data Structure
Each enhanced news entry contains:
```
{
  "news_id": "...",
  "seo_headline": "...",
  "rewritten_summary": "...",
  "image_prompt": "...",
  "image_path": "images/<news_id>_gemini.png",
  "image_id": "...",
  "tags": ["...", ...]
}
```
- `news_id` and `image_id` are the same for each article-image pair.

## Requirements
- Python 3.8+
- See `requirements.txt` for dependencies.

## Security
- Store API keys in environment variables or use a secrets manager for production.

## Extending
- Add more RSS feeds/topics via CLI.
- Integrate new AI models or image sources by extending the modular functions.
- Use the unique IDs for analytics, user tracking, or database storage.

---

For questions or contributions, open an issue or pull request!
