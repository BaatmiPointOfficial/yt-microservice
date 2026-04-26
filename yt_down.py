import yt_dlp
import os
import uuid
import requests
from urllib.parse import urlparse, parse_qs

def extract_yt_id(url):
    """Helper function to pull the video ID from standard links and Shorts"""
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        if "/shorts/" in parsed.path:
            return parsed.path.split("/shorts/")[1].split("?")[0]
        return parse_qs(parsed.query).get("v", [None])[0]
    elif "youtu.be" in parsed.netloc:
        return parsed.path[1:]
    return None

def download_youtube_video(video_url, output_folder="downloads", quality="720p"):
    try:
        os.makedirs(output_folder, exist_ok=True)
        random_id = uuid.uuid4().hex[:8]
        is_audio = (quality == "audio")
        ext = "mp3" if is_audio else "mp4"
        safe_filename = f"yt_{random_id}.{ext}"
        final_path = os.path.join(output_folder, safe_filename)

        # ---------------------------------------------------------
        # 🌟 YOUTUBE -> THE GOLDEN PROXY API
        # ---------------------------------------------------------
        if "youtube.com" in video_url or "youtu.be" in video_url:
            print("🔗 YouTube link detected! Routing to Golden Proxy API...")
            
            # The Exact API URL you provided
            api_url = "https://youtube-video-and-shorts-downloader.p.rapidapi.com/download.php"
            
            video_id = extract_yt_id(video_url)
            if not video_id:
                print("🚨 Could not extract YouTube ID from URL")
                return None, None, None
                
            # The Exact Parameter you provided
            querystring = {"id": video_id} 
            
            # The Exact Headers you provided
            headers = {
                "x-rapidapi-key": "03b30d167bmsh861ed6595bd1be2p1f639fjsnbcfcc274fa0a", # 🔴 PUT YOUR KEY HERE
                "x-rapidapi-host": "youtube-video-and-shorts-downloader.p.rapidapi.com",
                "Content-Type": "application/json"
            }
            
            # 1. Ask the Proxy API for the unlocked video link
            response = requests.get(api_url, headers=headers, params=querystring)
            
            if response.status_code != 200:
                print(f"🚨 API Request Failed! Status: {response.status_code}, Text: {response.text}")
                return None, None, None
                
            data = response.json()
            
            # 2. Safely hunt for the MP4 link in their JSON data
            direct_mp4_url = None
            if 'url' in data:
                direct_mp4_url = data['url']
            elif 'link' in data:
                direct_mp4_url = data['link']
            elif 'video' in data and 'url' in data['video']:
                direct_mp4_url = data['video']['url']
                
            if not direct_mp4_url:
                print(f"🚨 API Data Error (Could not find MP4 link): {data}")
                return None, None, None
                
            title = data.get('title', 'YouTube Media')
            thumbnail = data.get('thumbnail', '')

            # ---------------------------------------------------------
            # 🛡️ THE FINAL PATCH: CHUNKED STREAMING + DISGUISE
            # ---------------------------------------------------------
            print("🚀 Downloading MP4 from Proxy API in chunks...")
            
            # Disguise our Render server as a normal Windows Chrome Browser
            dl_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Stream the file to protect Render's free RAM
            with requests.get(direct_mp4_url, headers=dl_headers, stream=True) as r:
                r.raise_for_status() 
                with open(final_path, 'wb') as handler:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            handler.write(chunk)
                            
            print("✅ API Download & Save Complete!")
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