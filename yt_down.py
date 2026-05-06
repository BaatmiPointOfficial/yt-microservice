import os
import time
import yt_dlp  # The Ultimate Universal Engine!

def download_youtube_video(video_url, quality="720p"):
    """
    Directly extracts media from YT, Insta, TikTok, Facebook, X, etc.
    Bypasses 3rd party APIs entirely by running the extraction locally.
    """
    clean_url = video_url.strip()
    print(f"🚀 Universal Engine Extracting: {clean_url}")

    timestamp = int(time.time())
    
    # Ensure the downloads folder exists
    base_path = "downloads"
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    # 🌟 yt-dlp Configuration
    ydl_opts = {
        # Save file as: downloads/vaniconnect_123456_videoID.mp4
        'outtmpl': os.path.join(base_path, f'vaniconnect_{timestamp}_%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': False, # Set to False so we can see the download progress in Render logs!
    }

    # 🎛️ Quality Routing
    if quality == "audio":
        # Grabs the best audio stream directly. 
        ydl_opts['format'] = 'bestaudio/best'
    elif quality == "best":
        # Grabs the highest possible quality pre-merged MP4
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    else: 
        # Standard 720p or 480p fallback for speed
        ydl_opts['format'] = 'best[height<=720][ext=mp4]/best[ext=mp4]/best'

    try:
        # Boot up the yt-dlp engine
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # This single line handles the scraping, decrypting, and downloading!
            info = ydl.extract_info(clean_url, download=True)
            
            # Figure out exactly what filename it was saved as
            downloaded_file_path = ydl.prepare_filename(info)
            safe_filename = os.path.basename(downloaded_file_path)

            # Grab metadata for your React UI
            title = info.get('title', 'VaniConnect Media')
            thumbnail = info.get('thumbnail', 'https://via.placeholder.com/640x360.png?text=Media+Ready')

            print(f"✅ Success! Saved natively as {safe_filename}")
            return safe_filename, title, thumbnail

    except Exception as e:
        print(f"❌ Universal Downloader Error: {str(e)}")
        return None, None, None