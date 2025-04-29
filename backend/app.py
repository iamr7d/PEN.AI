from flask import Flask, jsonify, send_from_directory, abort, request
from flask_cors import CORS
import os
import json
import subprocess

app = Flask(__name__)
CORS(app)

NEWS_BUCKET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../news bucket'))
IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../images'))
DEFAULT_IMAGE = os.path.join(IMAGES_DIR, 'default.png')

@app.route('/images/<path:filename>')
def serve_image(filename):
    import os
    image_path = os.path.join(IMAGES_DIR, filename)
    if os.path.isfile(image_path):
        return send_from_directory(IMAGES_DIR, filename)
    else:
        # Serve default image if requested file is missing
        return send_from_directory(IMAGES_DIR, 'default.png')

@app.route('/api/news', methods=['GET'])
def get_news():
    try:
        # Aggregate all news from all .json files in NEWS_BUCKET_DIR
        news = []
        import glob
        for file in glob.glob(os.path.join(NEWS_BUCKET_DIR, '*.json')):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        news.extend(data)
                    elif isinstance(data, dict):
                        news.append(data)
            except Exception as e:
                continue  # Skip bad files
        # Enhance news items with tags and category if missing
        import re
        def clean_text(text):
            if not text:
                return text
            text = re.sub(r'\*\*', '', text)
            # Remove non-ASCII and emoji characters
            text = re.sub(r'[^\w\s.,!?\'\"-]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        categories = {
            'sports': ['football', 'cricket', 'tennis', 'sports', 'game', 'match'],
            'business': ['business', 'stock', 'market', 'finance', 'company'],
            'technology': ['tech', 'ai', 'robot', 'software', 'hardware', 'technology'],
            'science': ['science', 'research', 'study', 'scientist'],
            'entertainment': ['movie', 'film', 'music', 'celebrity', 'entertainment'],
            'world': ['world', 'international', 'global', 'war', 'country'],
            'health': ['health', 'covid', 'virus', 'doctor', 'hospital'],
            'politics': ['election', 'government', 'politics', 'minister', 'policy'],
            'crime': ['crime', 'attack', 'police', 'court', 'arrest', 'murder'],
            'environment': ['climate', 'environment', 'pollution', 'wildlife', 'nature'],
            'sports:football': ['football', 'soccer', 'premier league', 'fifa'],
            'sports:cricket': ['cricket', 'ipl', 'test match', 'odi'],
            'business:markets': ['stock market', 'share', 'index', 'sensex', 'nifty'],
        }
        def infer_category_and_subcategory(item):
            text = (item.get('seo_headline') or item.get('heading') or '').lower() + ' ' + (item.get('summary') or '')
            for cat, keywords in categories.items():
                if any(word in text for word in keywords):
                    if ':' in cat:
                        main_cat, sub_cat = cat.split(':', 1)
                        return main_cat.capitalize(), sub_cat.capitalize()
                    return cat.capitalize(), None
            return 'General', None
        def infer_tags(item):
            import collections
            if item.get('tags'):
                return item['tags']
            text = (item.get('seo_headline') or item.get('heading') or '') + ' ' + (item.get('summary') or '')
            words = [w.strip('.,!?').capitalize() for w in text.split() if len(w) > 4]
            common = [w for w, _ in collections.Counter(words).most_common(5)]
            return common
        def clean_tags(tags):
            # Accepts either a list or a comma-separated string
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',')]
            cleaned = []
            for tag in tags:
                if (
                    isinstance(tag, str) and
                    1 < len(tag) < 40 and
                    not any(x in tag.lower() for x in [
                        'here are', 'based on', 'tags for', 'summary:', 'headline', 'partial', 'news article'
                    ]) and
                    tag[0].isalpha()  # starts with a letter
                ):
                    cleaned.append(tag)
            return cleaned
        for item in news:
            # Clean paraphrased fields
            if item.get('seo_headline'):
                item['seo_headline'] = clean_text(item['seo_headline'])
            if item.get('rewritten_summary'):
                item['rewritten_summary'] = clean_text(item['rewritten_summary'])
            # Tags: always a list of strings, no weird objects
            if not item.get('tags') or not isinstance(item['tags'], (list, str)):
                item['tags'] = infer_tags(item)
            item['tags'] = clean_tags(item['tags'])
            # Remove any non-string tags
            item['tags'] = [t for t in item['tags'] if isinstance(t, str)]
            # Category and subcategory: always capitalized
            cat, subcat = infer_category_and_subcategory(item)
            item['category'] = cat
            item['subcategory'] = subcat
            # Date published (try to infer or set default)
            if not item.get('date_published'):
                item['date_published'] = item.get('date') or item.get('pubDate') or ''
            # Image: only filename, not path, and must exist in images bucket/general
            image_filename = os.path.basename(item.get('image', '').strip()) if item.get('image') else ''
            image_path = os.path.join(IMAGES_DIR, image_filename) if image_filename else ''
            # If explicit image field and file exists, use it
            if image_filename and os.path.isfile(image_path):
                item['image'] = image_filename
            else:
                # Try to find an image by UUID (news_id)
                news_id = item.get('news_id', '').strip()
                found_image = ''
                for ext in ['.jpg', '.jpeg', '.png']:
                    candidate = f"{news_id}{ext}"
                    candidate_path = os.path.join(IMAGES_DIR, candidate)
                    if news_id and os.path.isfile(candidate_path):
                        found_image = candidate
                        break
                item['image'] = found_image  # Only set if real file exists, else ''
            # Ensure required fields exist
            for key in ['news_id','heading','summary','link','category','date_published','image']:
                if key not in item:
                    item[key] = ''
        return jsonify(news)


    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/news/<news_id>', methods=['GET'])
def get_news_item(news_id):
    try:
        # Aggregate all news from all .json files in NEWS_BUCKET_DIR
        news = []
        import glob
        for file in glob.glob(os.path.join(NEWS_BUCKET_DIR, '*.json')):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        news.extend(data)
                    elif isinstance(data, dict):
                        news.append(data)
            except Exception:
                continue
        for item in news:
            if str(item.get('news_id')) == str(news_id):
                return jsonify(item)
        return jsonify({'error': 'News item not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/images/<path:filename>', methods=['GET'])
def get_image(filename):
    if os.path.exists(os.path.join(IMAGES_DIR, filename)):
        return send_from_directory(IMAGES_DIR, filename)
    else:
        abort(404)

# --- Secure update-content endpoint ---
@app.route('/api/update-content', methods=['POST'])
def update_content():
    data = request.get_json(force=True)
    secret = data.get('secret')
    # Set your secret key here
    SECRET_KEY = os.environ.get('UPDATE_SECRET', 'pen_secret_123')
    if secret != SECRET_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        result = subprocess.run(['python', '../update_content.py'], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({'status': 'success', 'output': result.stdout})
        else:
            return jsonify({'status': 'error', 'output': result.stderr}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'output': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
