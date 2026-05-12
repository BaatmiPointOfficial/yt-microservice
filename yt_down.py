import os
import yt_dlp
import time

def download_youtube_video(video_url, quality="720p"):
    """
    Dedicated YouTube-Only Engine for V1 Launch.
    Lightning fast, highly stable.
    """
    print(f"🚀 Launching YouTube Engine for: {video_url}")

    timestamp = int(time.time())
    output_folder = "downloads"
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    ydl_opts = {
        # Drops the 720p height limit completely to guarantee a match
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{output_folder}/vaniconnect_{timestamp}_%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': False,
        'cookiefile': 'cookies.txt' 
    }

    if quality == "audio":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download the video
            info_dict = ydl.extract_info(video_url, download=True)
            
            # Find out what the file was actually named
            downloaded_file_path = ydl.prepare_filename(info_dict)
            if quality == "audio":
                downloaded_file_path = downloaded_file_path.rsplit('.', 1)[0] + '.mp3'
            
            safe_filename = os.path.basename(downloaded_file_path)
            title = info_dict.get('title', 'VaniConnect Video')
            thumbnail = info_dict.get('thumbnail', 'https://via.placeholder.com/640x360.png?text=Media+Ready')

            print(f"✅ Success! Downloaded: {title}")
            return safe_filename, title, thumbnail

    except Exception as e:
        print(f"🚨 YouTube Engine Error: {str(e)}")
        return None, None, None