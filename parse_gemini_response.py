def parse_gemini_response(text):
    """
    Parse the Gemini model's response into headline, summary, full article, and image prompt fields.
    Expects format:
    Headline: ...
    Summary: ...
    Full Article: ...
    Also, generate a prompt for an illustration image that matches the news.
    """
    headline = ''
    summary = ''
    full_text = ''
    image_prompt = ''
    lines = text.splitlines()
    current = None
    for line in lines:
        line = line.strip()
        if line.lower().startswith('headline:'):
            current = 'headline'
            headline = line.partition(':')[2].strip()
        elif line.lower().startswith('summary:'):
            current = 'summary'
            summary = line.partition(':')[2].strip()
        elif line.lower().startswith('full article:'):
            current = 'full_text'
            full_text = line.partition(':')[2].strip()
        elif 'illustration' in line.lower() or 'image' in line.lower():
            current = 'image_prompt'
            image_prompt = line.partition(':')[2].strip()
        elif current == 'summary' and line:
            summary += '\n' + line
        elif current == 'full_text' and line:
            full_text += '\n' + line
    return {'seo_headline': headline, 'rewritten_summary': summary, 'rewritten_full_text': full_text, 'image_prompt': image_prompt}
