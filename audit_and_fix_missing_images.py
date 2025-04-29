import os
import json

ENHANCED_NEWS_PATH = os.path.join('news bucket', 'enhanced_news.json')
IMAGES_DIR = 'images'
DEFAULT_IMAGE = os.path.join(IMAGES_DIR, 'default.png')
BACKUP_PATH = os.path.join('news bucket', 'enhanced_news_backup.json')

def audit_and_fix():
    # Backup original JSON
    if os.path.exists(ENHANCED_NEWS_PATH):
        with open(ENHANCED_NEWS_PATH, 'r', encoding='utf-8') as f:
            news = json.load(f)
        with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
    else:
        print(f"{ENHANCED_NEWS_PATH} not found!")
        return

    fixed = False
    for article in news:
        image_path = article.get('image_path')
        if not image_path or not os.path.isfile(image_path):
            # Try to resolve relative path if needed
            if image_path and not os.path.isabs(image_path):
                abs_path = os.path.join(IMAGES_DIR, os.path.basename(image_path))
            else:
                abs_path = image_path
            if not abs_path or not os.path.isfile(abs_path):
                article['image_path'] = DEFAULT_IMAGE
                fixed = True
                print(f"Fixed missing image for article: {article.get('news_id', article.get('heading', 'UNKNOWN'))}")
    if fixed:
        with open(ENHANCED_NEWS_PATH, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        print("All missing images fixed. Backup saved as enhanced_news_backup.json.")
    else:
        print("No missing images found.")

if __name__ == '__main__':
    audit_and_fix()
