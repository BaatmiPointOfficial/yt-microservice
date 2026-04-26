import yt_dlp
import os
import uuid

def download_youtube_video(video_url, output_folder="downloads", quality="720p"):
    try:
        os.makedirs(output_folder, exist_ok=True)
        random_id = uuid.uuid4().hex[:8]
        is_audio = (quality == "audio")
        ext = "mp3" if is_audio else "mp4"
        safe_filename = f"yt_{random_id}.{ext}"
        final_path = os.path.join(output_folder, safe_filename)

        print("🔗 Link detected! Using pure native yt-dlp engine with Passport...")
        
        if quality == "best":
            format_str = 'bestvideo+bestaudio/best'
        elif quality == "720p":
            format_str = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        elif quality == "480p":
            format_str = 'bestvideo[height<=480]+bestaudio/best[height<=480]/best'
        elif quality == "audio":
            format_str = 'bestaudio/best'
        else:
            format_str = 'best' 
            
        ydl_opts = {
            'format': format_str, 
            'outtmpl': final_path,  
            'quiet': False,
            'no_warnings': True,
            # 🛡️ THE MAGIC BYPASS: Giving YouTube your Human Passport
            'cookiefile': 'cookies.txt',  # Matches your exact file name!
        }
        
        if is_audio:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            ydl_opts['merge_output_format'] = 'mp4'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            title = info_dict.get('title', 'Unknown Media')
            thumbnail = info_dict.get('thumbnail', '')
            
        print("✅ Native Download Complete!")
        return safe_filename, title, thumbnail
            
    except Exception as e:
        print(f"🚨 Engine Error: {e}")
        return None, None, None