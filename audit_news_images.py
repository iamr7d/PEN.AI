import os
import json

NEWS_JSON_PATH = 'enhanced_news.json'
IMAGES_DIR = 'images'

with open(NEWS_JSON_PATH, 'r', encoding='utf-8') as f:
    news = json.load(f)

missing_images = []
for item in news:
    image_path = item.get('image_path')
    if image_path:
        # Extract filename only, handle both / and \
        filename = image_path.replace('\\', '/').split('/')[-1]
        full_path = os.path.join(IMAGES_DIR, filename)
        if not os.path.isfile(full_path) or os.path.getsize(full_path) == 0:
            missing_images.append({'news_id': item.get('news_id'), 'image_path': image_path, 'headline': item.get('heading')})
    else:
        missing_images.append({'news_id': item.get('news_id'), 'image_path': None, 'headline': item.get('heading')})

if missing_images:
    print(f"Found {len(missing_images)} news items with missing or invalid images:\n")
    for m in missing_images:
        print(f"news_id: {m['news_id']} | image_path: {m['image_path']} | headline: {m['headline']}")
else:
    print("All news items have valid images!")
