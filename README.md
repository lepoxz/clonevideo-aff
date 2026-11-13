# CloneVideo-Aff MVP

**Research Crawl Viral Video (Instagram, Facebook, Threads, Meta Ads Library) + Muse Token Pool Video Cloner + Smart Affiliate Publisher (Auto First-Comment Link & Link-in-Bio).**

## Tech Stack
- **Backend**: Python 3.11 + FastAPI + SQLite + Async Worker Queue
- **Free Crawler**: Crawl4AI / Playwright + `yt-dlp` (Zero paid API required; optional `treg.to` integration)
- **Video Processing & Muse Cloner**: Muse Bulk Token Pool Rotator (1B Token Accounts) + Pillow Vietnamese CTA Overlay Renderer + FFmpeg 9:16 Vertical Composer
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS + Lucide React

## Quick Start
Run `start-dev.bat` or start separately:
1. Backend:
   ```powershell
   cd backend
   C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev -- --port 5173
   ```

## Repository
Remote: `https://github.com/lepoxz/clonevideo-aff.git`
