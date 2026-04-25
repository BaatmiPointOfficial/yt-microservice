import yt_dlp
import os
import uuid
import requests
from urllib.parse import urlparse, parse_qs

def extract_yt_id(url):
    """Helper function to pull the video ID from normal links and Shorts"""
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
            
            # NOTE: In RapidAPI, make sure you click the endpoint for "Video Details" or "Download"
            # Update this URL if the dashboard gives you a slightly different one for videos!
            api_url = "https://youtube-video-and-shorts-downloader1.p.rapidapi.com/api/v1/video" 
            
            # Extract the ID from the user's URL
            video_id = extract_yt_id(video_url)
            querystring = {"id": video_id} 
            
            headers = {
                "x-rapidapi-key": "03b30d167bmsh861ed6595bd1be2p1f639fjsnbcfcc274fa0a", # 👈 PASTE YOUR REAL KEY HERE
                "x-rapidapi-host": "youtube-video-and-shorts-downloader1.p.rapidapi.com"
            }
            
            # 1. Ask the Proxy API for the unlocked video link
            response = requests.get(api_url, headers=headers, params=querystring)
            data = response.json()
            
            direct_mp4_url = None
            
            # Safely hunt for the MP4 link in their JSON data
            if 'url' in data:
                direct_mp4_url = data['url']
            elif 'video' in data and 'url' in data['video']:
                direct_mp4_url = data['video']['url']
            elif 'links' in data:
                direct_mp4_url = data['links'][0] # Grab highest quality
                
            if not direct_mp4_url:
                print(f"🚨 API Data Error (Check RapidAPI JSON structure): {data}")
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
        # 🌟 INSTAGRAM / TWITTER -> NATIVE yt-dlp ENGINE
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