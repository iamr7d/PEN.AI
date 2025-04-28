from flask import Flask, jsonify, send_from_directory, abort, request
from flask_cors import CORS
import os
import json
import subprocess

app = Flask(__name__)
CORS(app)

NEWS_JSON_PATH = os.path.join(os.path.dirname(__file__), '../enhanced_news.json')
IMAGES_DIR = os.path.join(os.path.dirname(__file__), '../images')

@app.route('/api/news', methods=['GET'])
def get_news():
    try:
        with open(NEWS_JSON_PATH, 'r', encoding='utf-8') as f:
            news = json.load(f)
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
            # Tags
            if not item.get('tags'):
                item['tags'] = infer_tags(item)
            # Always clean tags
            item['tags'] = clean_tags(item['tags'])
            # Category and subcategory
            if not item.get('category') or not item.get('subcategory'):
                cat, subcat = infer_category_and_subcategory(item)
                item['category'] = cat
                item['subcategory'] = subcat
            # Date published (try to infer or set default)
            if not item.get('date_published'):
                item['date_published'] = item.get('date') or item.get('pubDate') or ''
        return jsonify(news)


    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/news/<news_id>', methods=['GET'])
def get_news_item(news_id):
    try:
        with open(NEWS_JSON_PATH, 'r', encoding='utf-8') as f:
            news = json.load(f)
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
