# Video Downloader Web App

A Flask web application to download videos and audio from YouTube, TikTok, Instagram, and Twitter. Includes user authentication, download history, and a modern UI.

## Features
- Download videos (MP4) and audio (MP3) from YouTube, TikTok, Instagram, and Twitter
- User signup, login, and download history
- Download in various resolutions and formats
- Mobile-friendly, modern interface
- Admin can delete downloads

## Local Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd <your-repo>
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the app:**
   ```bash
   python app.py
   ```
4. **Visit:**
   Open [http://localhost:5000](http://localhost:5000) in your browser.


## Notes
- For persistent storage, consider using a managed database (SQLite resets on redeploy).
- Downloading from some platforms may be subject to their terms of service. 
