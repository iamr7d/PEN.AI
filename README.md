# Planet Earth News (PEN)

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![React](https://img.shields.io/badge/React-18+-61dafb?logo=react)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3+-06b6d4?logo=tailwindcss)

## Overview
**PEN** (Planet Earth News) is a modern AI-powered news platform. It aggregates news from multiple sources, enhances headlines and summaries using Google Gemini, generates tags, and creates SEO-friendly images for each article. Each article is uniquely identified and visually branded for a premium user experience.

---

## Features
- 🌍 Aggregates news from RSS feeds, Google News, and NewsAPI
- 🧠 Enhances headlines and summaries with Gemini AI
- 🏷️ Generates relevant tags for each article
- 🖼️ Creates SEO-optimized images using Gemini API (with Unsplash fallback)
- 🆔 Robust data: every article and image gets a unique UUID
- 💾 Saves all outputs in both JSON and CSV formats
- ⚡ Fast, modular, and extensible Python backend (Flask)
- ⚛️ Modern React frontend with Tailwind CSS
- 🌗 **Dark mode toggle** and responsive UI
- 🦾 Accessible navigation and keyboard support
- 🖌️ SVG branding (R7D logo), beautiful cards, and trending/related articles

---

## Quick Start

### 1. Backend (Flask)
```bash
cd backend
pip install -r requirements.txt
python app.py
```
- Runs the API at `http://localhost:5000`

### 2. Frontend (React)
```bash
cd frontend
npm install
npm start
```
- Runs the UI at `http://localhost:3000`

---

## Usage

### Aggregate & Enhance News
- See scripts: `aggregate_news.py`, `gemini_news_enhancer.py`, etc. (see below)

### Data Structure Example
```json
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

---

## Notable UI Features
- **Dark/Light mode** (toggle, persists user choice)
- **Trending & Related articles** with clickable cards
- **SVG R7D logo** in header (right corner)
- **Newsletter signup** and accessible navigation
- **Responsive**: works on desktop, tablet, and mobile
- **No backend info or debug shown in UI**
- **Consistent design** with Inter/Montserrat fonts

---

## Contributing
1. Fork the repo and clone your fork
2. Create a new branch for your feature/fix
3. Commit and push your changes
4. Open a pull request!

---

## Deployment
- Push to your GitHub repo
- Deploy backend (Flask) and frontend (React) to your preferred platform (e.g., Vercel, Netlify, Heroku, Render, etc.)

---

## License
MIT

---

## Authors
- [R7D Team](https://github.com/iamr7d)

---

For questions or support, open an issue or contact the maintainers.

- Store API keys in environment variables or use a secrets manager for production.

## Extending
- Add more RSS feeds/topics via CLI.
- Integrate new AI models or image sources by extending the modular functions.
- Use the unique IDs for analytics, user tracking, or database storage.

---

For questions or contributions, open an issue or pull request!
