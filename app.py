# ---------- app.py ----------
from flask import Flask, render_template, request, redirect, session, jsonify, send_from_directory
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from yt_dlp import YoutubeDL
import os
import sqlite3
import re
from datetime import datetime
from utils.security import sanitize_input, create_password_hash, verify_password_hash
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here')
if app.secret_key == 'your_secret_key_here':
    print('WARNING: Using default secret key! Set SECRET_KEY in your .env file for production.')
csrf = CSRFProtect(app)

# Create necessary directories
DOWNLOAD_DIR = os.path.join(app.root_path, 'downloads')
DB_DIR = os.path.join(app.root_path, 'data')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, 'users.db')

# ---------- DB ----------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                file_path TEXT,
                date TEXT,
                platform TEXT
            )
        ''')

def ensure_platform_column():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(downloads)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'platform' not in columns:
            try:
                cursor.execute('ALTER TABLE downloads ADD COLUMN platform TEXT')
                conn.commit()
                print('Added platform column to downloads table.')
            except Exception as e:
                print(f'Error adding platform column: {e}')

# Initialize database
init_db()
ensure_platform_column()

# ---------- HELPER FUNCTIONS ----------
def detect_platform(url):
    """Detect which platform the URL belongs to."""
    # TikTok URL patterns
    if re.search(r'(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)\/', url):
        return "tiktok"
    
    # Instagram URL patterns - catch posts, reels, stories, etc.
    if re.search(r'(instagram\.com|instagr\.am)\/(?:p|reel|tv|stories)\/[\w-]+', url):
        return "instagram"
    
    # Twitter/X URL patterns
    if re.search(r'(twitter\.com|x\.com)\/(?:[\w]+)\/status\/(?:\d+)', url):
        return "twitter"
    
    # Facebook URL patterns
    if re.search(r'(facebook\.com|fb\.com|fb\.watch)\/(?:[\w\.]+\/videos\/|watch\?v=)[\w\.]+', url):
        return "facebook"
    
    # YouTube patterns
    if re.search(r'(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)[\w-]+', url):
        return "youtube"
    
    # If no specific match, try a more general approach based on domain
    if "tiktok" in url:
        return "tiktok"
    elif "instagram" in url or "instagr.am" in url:
        return "instagram"
    elif "twitter" in url or "x.com" in url:
        return "twitter"
    elif "facebook" in url or "fb.com" in url or "fb.watch" in url:
        return "facebook"
    elif "youtube" in url or "youtu.be" in url:
        return "youtube"
    
    # Default to YouTube as fallback
    return "youtube"

def create_download_options(url, file_format, resolution=None):
    """Create appropriate download options based on the URL and format."""
    platform = detect_platform(url)
    directory = DOWNLOAD_DIR
    # Limit title to 80 characters and restrict filenames to safe characters
    output_template = os.path.join(directory, '%(title).80s.%(ext)s')
    
    # Base options
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'postprocessors': [],
        'restrictfilenames': True,  # Only allow safe characters in filenames
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    # Platform-specific settings
    if platform == "youtube":
        ydl_opts.update({
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            'merge_output_format': 'mp4',
            'postprocessor_args': {
                'ffmpeg': [
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-ac', '2',
                    '-vsync', '0'
                ]
            }
        })
    elif platform == "tiktok":
        ydl_opts.update({
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Referer': 'https://www.tiktok.com/'
            },
            'format': 'bestvideo+bestaudio/best'
        })
    elif platform == "instagram":
        ydl_opts.update({
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Referer': 'https://www.instagram.com/'
            },
            'format': 'bestvideo+bestaudio/best',
            'sleep_interval': 1,
            'max_sleep_interval': 5
        })
    elif platform == "twitter":
        ydl_opts.update({
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Referer': 'https://twitter.com/'
            },
            'format': 'bestvideo+bestaudio/best'
        })
    elif platform == "facebook":
        ydl_opts.update({
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Referer': 'https://www.facebook.com/'
            },
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            'sleep_interval': 1,
            'max_sleep_interval': 5
        })
    
    # Configure based on format
    if file_format == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
    else:  # MP4 video
        if resolution:
            if int(resolution) >= 1440:
                ydl_opts['format'] = f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]/best'
            else:
                ydl_opts['format'] = f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]/best'
        
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        })
    
    return ydl_opts

def resolve_tiktok_shortlink(url):
    if 'vt.tiktok.com' in url or 'vm.tiktok.com' in url:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            return resp.url
        except Exception as e:
            print(f"Error resolving TikTok shortlink: {e}")
            return url
    return url

def is_tiktok_photo_url(url):
    # TikTok photo posts use /photo/ in the URL
    return 'tiktok.com/' in url and '/photo/' in url

# ---------- ROUTES ----------
@app.route('/')
def home():
    # Always render home, pass username if available
    return render_template('index.html', username=session.get('username'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = sanitize_input(request.form['username'])
        try:
            password = create_password_hash(request.form['password'])
        except ValueError as ve:
            return str(ve)
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            return redirect('/login')
        except sqlite3.IntegrityError:
            return 'Username already exists!'
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = sanitize_input(request.form['username'])
        password = request.form['password']
        with sqlite3.connect(DB_PATH) as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and verify_password_hash(user[2], password):
                session['username'] = username
                return redirect('/')
        return 'Invalid credentials!'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

@app.route('/video_info', methods=['POST'])
@csrf.exempt
def video_info():
    data = request.get_json(force=True)
    url = data.get('url')
    url = resolve_tiktok_shortlink(url)
    if is_tiktok_photo_url(url):
        return jsonify({'error': 'TikTok photo posts are not supported. Please use a TikTok video link.'})
    try:
        platform = detect_platform(url)
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Format platform-specific data
            if platform == "tiktok":
                title = f"TikTok: {info.get('title') or 'Video'}"
                description = f"Creator: {info.get('uploader') or 'Unknown'}"
            elif platform == "instagram":
                title = f"Instagram: {info.get('title') or 'Video/Reel'}"
                description = f"Creator: {info.get('uploader') or 'Unknown'}"
            elif platform == "twitter":
                title = f"Twitter: {info.get('title') or 'Tweet Video'}"
                description = f"Creator: {info.get('uploader') or 'Unknown'}"
            elif platform == "facebook":
                title = f"Facebook: {info.get('title') or 'Video'}"
                description = f"Creator: {info.get('uploader') or 'Unknown'}"
            else:
                title = info.get('title')
                description = info.get('description')
                
            return jsonify({
                'title': title,
                'description': description,
                'platform': platform
            })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download', methods=['POST'])
@csrf.exempt
def download():
    if 'username' not in session:
        return 'Unauthorized', 401

    try:
        data = request.get_json(force=True)
        url = data.get('url')
        url = resolve_tiktok_shortlink(url)
        if is_tiktok_photo_url(url):
            return jsonify({'error': 'TikTok photo posts are not supported. Please use a TikTok video link.'}), 400
        file_format = data.get('format', 'mp4')
        resolution = data.get('resolution')
        
        # Detect platform and create appropriate download options
        platform = detect_platform(url)
        ydl_opts = create_download_options(url, file_format, resolution)
        
        # Add warning for high-res videos
        warning_message = None
        if resolution and int(resolution) >= 1440:
            warning_message = f"Downloading in {resolution}p may take longer and require more storage space."
        
        # Add platform-specific information to warning message
        if platform == "tiktok":
            platform_msg = "TikTok video download started."
        elif platform == "instagram":
            platform_msg = "Instagram content download started."
        elif platform == "twitter":
            platform_msg = "Twitter video download started."
        else:
            platform_msg = "YouTube video download started."
            
        # Combine messages if both exist
        if warning_message:
            warning_message = f"{platform_msg} {warning_message}"
        else:
            warning_message = platform_msg

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if file_format == 'mp3':
                filename = os.path.splitext(filename)[0] + '.mp3'
            elif file_format == 'mp4' and not filename.endswith('.mp4'):
                # Ensure correct extension for MP4 files
                filename = os.path.splitext(filename)[0] + '.mp4'

        # Prepend platform name to the filename for easier identification in history
        original_name = os.path.basename(filename)
        if platform != "youtube" and not original_name.startswith(platform.capitalize()):
            new_name = f"{platform.capitalize()}-{original_name}"
            new_path = os.path.join(DOWNLOAD_DIR, new_name)
            orig_path = os.path.join(DOWNLOAD_DIR, original_name)
            if os.path.exists(new_path):
                # Add a unique suffix if file exists
                base, ext = os.path.splitext(new_name)
                unique_name = f"{base}-{uuid.uuid4().hex[:8]}{ext}"
                new_path = os.path.join(DOWNLOAD_DIR, unique_name)
                os.rename(orig_path, new_path)
                final_name = unique_name
            else:
                os.rename(orig_path, new_path)
                final_name = new_name
        else:
            final_name = original_name

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('INSERT INTO downloads (username, file_path, date, platform) VALUES (?, ?, ?, ?)',
                         (session['username'], final_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), platform))

        response_data = {'success': True, 'filename': final_name, 'platform': platform}
        if warning_message:
            response_data['warning'] = warning_message
            
        return jsonify(response_data)

    except Exception as e:
        print("❌ Download error:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/my_downloads')
def my_downloads():
    username = session.get('username')
    downloads = []
    if username:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                # Check if platform column exists in the downloads table
                try:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(downloads)")
                    columns = [info[1] for info in cursor.fetchall()]
                    
                    if 'platform' in columns:
                        downloads = conn.execute('''
                            SELECT file_path, date, platform FROM downloads 
                            WHERE username = ? ORDER BY date DESC
                        ''', (username,)).fetchall()
                    else:
                        # If platform column doesn't exist, use old query
                        downloads = conn.execute('''
                            SELECT file_path, date FROM downloads 
                            WHERE username = ? ORDER BY date DESC
                        ''', (username,)).fetchall()
                except Exception as e:
                    # Fallback to basic query if there was an error
                    print(f"Error checking schema: {e}")
                    downloads = conn.execute('''
                        SELECT file_path, date FROM downloads 
                        WHERE username = ? ORDER BY date DESC
                    ''', (username,)).fetchall()
        except sqlite3.Error as e:
            print(f"Database error fetching downloads for {username}: {e}")
            # Optionally add flash message for the user

    return render_template('download.html', username=username, downloads=downloads)

@app.route('/download/<path:filename>')
def serve_file(filename):
    return send_from_directory(directory=DOWNLOAD_DIR, path=filename, as_attachment=True)

@app.route('/delete_download/<path:filename>', methods=['DELETE'])
def delete_download(filename):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # The filename from the route is URL-decoded by Flask.
    # We trust this filename as it corresponds to what's in the DB.
    # Path traversal is prevented by joining with DOWNLOAD_DIR and checking existence within it.
    file_path = os.path.join(DOWNLOAD_DIR, filename)

    # Security check: Ensure the resolved path is actually within DOWNLOAD_DIR
    if not os.path.abspath(file_path).startswith(os.path.abspath(DOWNLOAD_DIR)):
        print(f"Attempted path traversal: {filename}")
        return jsonify({'error': 'Invalid path'}), 400

    try:
        # 1. Delete the file from filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            # If file doesn't exist, maybe still allow deleting DB record?
            # Or return error? For now, proceed to delete DB record.
            print(f"Warning: File not found for deletion, but proceeding with DB removal: {file_path}")

        # 2. Delete the record from the database
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Match username AND filename for security
            cursor.execute('DELETE FROM downloads WHERE username = ? AND file_path = ?',
                           (session['username'], filename)) # Use original filename
            deleted_rows = cursor.rowcount
            conn.commit()

        if deleted_rows == 0:
            # This could happen if the file existed but the DB record didn't, or vice-versa
            # Or if the filename didn't match the user's records
            print(f"Warning: No database record found for user '{session['username']}' and file '{filename}'")
            # Still return success as the goal is to remove it from the user's view

        return jsonify({'success': True})

    except sqlite3.Error as db_err:
        print(f"❌ Database error during deletion: {db_err}")
        return jsonify({'error': 'Database error during deletion.'}), 500
    except OSError as os_err:
        print(f"❌ Filesystem error during deletion: {os_err}")
        return jsonify({'error': 'Filesystem error during deletion.'}), 500
    except Exception as e:
        print(f"❌ Unexpected error during deletion: {e}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

# ---------- START ----------
if __name__ == '__main__':
    app.run()