import os
import re
import requests
import google.generativeai as genai
from PIL import Image
from io import BytesIO

import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def generate_image(prompt, gemini_api_key=None, unsplash_access_key=None, out_dir='images', filename_hint='image', category=None):
    """
    Generate an image using Gemini API, or fallback to Unsplash if Gemini fails.
    Returns a dict with image_path and image_id.
    """
    # Use category subfolder if provided
    if category:
        out_dir = os.path.join('images bucket', category.lower().replace(' ', '_'))
    else:
        out_dir = 'images bucket/general'
    os.makedirs(out_dir, exist_ok=True)
    image_path = None
    # Try Gemini first if API key provided
    if gemini_api_key:
        try:
            genai.configure(api_key=gemini_api_key)
            model_name = 'imagen-3.0-generate-002'
            print(f"[Gemini] Using model: {model_name}")
            image_model = genai.GenerativeModel(model_name)
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
            response = call_with_retry(image_model, prompt)

            image_bytes = None
            for part in getattr(response, 'parts', []):
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    break
            if image_bytes:
                safe_name = re.sub(r'[^A-Za-z0-9_-]', '', filename_hint[:50].replace(' ', '_'))
                image_path = os.path.join(out_dir, f"{safe_name}_gemini.png")
                image = Image.open(BytesIO(image_bytes))
                image.save(image_path)
                return {'image_path': image_path, 'image_id': safe_name}
        except Exception as e:
            print(f"Gemini image generation failed: {e}")
    # Fallback: Unsplash
    if unsplash_access_key:
        try:
            url = f"https://api.unsplash.com/photos/random?query={requests.utils.quote(prompt)}&client_id={unsplash_access_key}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                img_url = data.get('urls', {}).get('regular')
                if img_url:
                    img_data = requests.get(img_url, timeout=10).content
                    safe_name = re.sub(r'[^A-Za-z0-9_-]', '', filename_hint[:50].replace(' ', '_'))
                    image_path = os.path.join(out_dir, f"{safe_name}_unsplash.jpg")
                    with open(image_path, 'wb') as out_img:
                        out_img.write(img_data)
                    return {'image_path': image_path, 'image_id': safe_name}
        except Exception as ue:
            print(f"Unsplash fallback failed: {ue}")
    return None

if __name__ == "__main__":
    setup_logging()
    import argparse
    parser = argparse.ArgumentParser(description="Generate an image from a prompt using Gemini or Unsplash.")
    parser.add_argument('--prompt', required=True, help='Image generation prompt')
    parser.add_argument('--filename', default='image', help='Filename hint for the image')
    parser.add_argument('--gemini_key', default=None, help='Gemini API Key')
    parser.add_argument('--unsplash_key', default=None, help='Unsplash Access Key')
    parser.add_argument('--out_dir', default='images bucket', help='Output directory (default: images bucket)')
    parser.add_argument('--category', default=None, help='Category for bucketing images')
    args = parser.parse_args()

    result = generate_image(args.prompt, args.gemini_key, args.unsplash_key, args.out_dir, args.filename, args.category)
    if result:
        print(f"Image saved to: {result['image_path']}")
        print(f"Image ID: {result['image_id']}")
    else:
        print("Image generation failed.")
