import os
import json

def fix_image_paths(json_path):
    images_dir = 'images'
    with open(json_path, 'r', encoding='utf-8') as f:
        news = json.load(f)
    changed = False
    for item in news:
        img = item.get('image_path')
        news_id = item.get('news_id')
        # Always force update if missing, set to default, or invalid
        needs_update = (not img) or (img == 'default.png')
        filename = os.path.basename(str(img).replace('\\', '/')) if img else None
        full_path = os.path.join(images_dir, filename) if filename else None
        if needs_update or not filename or not os.path.isfile(full_path) or os.path.getsize(full_path) == 0:
            # Try to find a file in images/ that starts with the news_id
            found = False
            if news_id:
                for f in os.listdir(images_dir):
                    if f.startswith(news_id):
                        item['image_path'] = f
                        found = True
                        changed = True
                        break
            if not found:
                item['image_path'] = 'default.png'
                changed = True
        else:
            if filename != img:
                item['image_path'] = filename
                changed = True
    if changed:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        print(f"Patched image_path in {json_path}")
    else:
        print(f"No changes needed in {json_path}")

if __name__ == "__main__":
    for fname in [
        'enhanced_news.json',
        'news bucket/enhanced_news.json',
        'all_news.json',
        'news bucket/news_technology.json',
        'frontend/public/enhanced_news.json',
    ]:
        if os.path.exists(fname):
            fix_image_paths(fname)
