import yt_dlp
import os
import uuid
import requests

def download_youtube_video(video_url, output_folder="downloads", quality="720p"):
    try:
        os.makedirs(output_folder, exist_ok=True)
        random_id = uuid.uuid4().hex[:8]
        is_audio = (quality == "audio")
        ext = "mp3" if is_audio else "mp4"
        safe_filename = f"yt_{random_id}.{ext}"
        final_path = os.path.join(output_folder, safe_filename)

        # ---------------------------------------------------------
        # 🌟 YOUTUBE -> COBALT OPEN-SOURCE PROXY (100% FREE)
        # ---------------------------------------------------------
        if "youtube.com" in video_url or "youtu.be" in video_url:
            print("🔗 YouTube link detected! Routing to Cobalt Open-Source API...")
            
            # The public Cobalt API endpoint
            api_url = "https://api.cobalt.tools/api/json"
            
            # Cobalt requires specific headers to know we aren't a malicious bot
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            # We tell Cobalt exactly what we want
            payload = {
                "url": video_url,
                "vQuality": "720",          # Force 720p to save Render's memory
                "isAudioOnly": is_audio     # Handle audio toggle
            }
            
            # 1. Ask Cobalt to process the video and give us the proxied link
            response = requests.post(api_url, json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"🚨 Cobalt API Error! Status: {response.status_code}, Text: {response.text}")
                return None, None, None
                
            data = response.json()
            
            # 2. Extract the clean download link
            if data.get("status") in ["redirect", "stream", "success"]:
                direct_mp4_url = data.get("url")
            else:
                print(f"🚨 Cobalt Data Error (Could not find proxied link): {data}")
                return None, None, None
                
            # Note: Cobalt doesn't return titles/thumbnails in the basic JSON, 
            # so we set fallbacks to keep the frontend happy.
            title = "YouTube Media Download" 
            thumbnail = "" 

            # ---------------------------------------------------------
            # 🛡️ THE STREAMING PATCH (Protecting Render's Memory)
            # ---------------------------------------------------------
            print("🚀 Downloading MP4 from Cobalt Proxy in chunks...")
            
            # Stream the file from Cobalt's servers to our Render server
            with requests.get(direct_mp4_url, headers=headers, stream=True) as r:
                r.raise_for_status() 
                with open(final_path, 'wb') as handler:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            handler.write(chunk)
                            
            print("✅ Cobalt Download & Save Complete!")
            return safe_filename, title, thumbnail

        # ---------------------------------------------------------
        # 🌟 INSTAGRAM / TWITTER -> NATIVE ENGINE
        # ---------------------------------------------------------
        else:
            print("🔗 Non-YouTube link detected! Using native yt-dlp...")
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
                'source_address': '0.0.0.0',
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
                
            return safe_filename, title, thumbnail
            
    except Exception as e:
        print(f"🚨 Engine Error: {e}")
        return None, None, None