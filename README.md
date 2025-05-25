# Video Downloader Web App

A Flask web application to download videos and audio from YouTube, TikTok, Instagram, and Twitter. Includes user authentication, download history, and a modern UI.

## Features
- Download videos (MP4) and audio (MP3) from YouTube, TikTok, Instagram, and Twitter
- User signup, login, and download history
- Download in various resolutions and formats
- Mobile-friendly, modern interface
- Admin can delete downloads

## Prerequisites

### FFmpeg Installation
FFmpeg is required for video processing. Install it based on your operating system:

**Windows:**
1. Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract the downloaded zip file
3. Add FFmpeg's bin folder to your system's PATH environment variable
4. Verify installation by opening a new terminal and typing: `ffmpeg -version`

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

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
