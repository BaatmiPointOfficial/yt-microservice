import yt_dlp
import os
import uuid
import requests
from urllib.parse import urlparse, parse_qs

def extract_yt_id(url):
    """Helper function to pull the video ID from the link"""
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
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
        # 🌟 THE HYBRID ROUTER: YOUTUBE -> RAPID API
        # ---------------------------------------------------------
        if "youtube.com" in video_url or "youtu.be" in video_url:
            print("🔗 YouTube link detected! Routing to Free RapidAPI...")
            video_id = extract_yt_id(video_url)
            
            # The correct Video Download Endpoint
            api_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
            querystring = {"videoId": video_id}
            headers = {
                "x-rapidapi-key": "03b30d167bmsh861ed6595bd1be2p1f639fjsnbcfcc274fa0a",
                "x-rapidapi-host": "youtube-media-downloader.p.rapidapi.com"
            }
            
            response = requests.get(api_url, headers=headers, params=querystring)
            data = response.json()
            
            direct_mp4_url = None
            
            # Safely extract the MP4 link from the API's JSON response
            if 'videos' in data and 'items' in data['videos']:
                direct_mp4_url = data['videos']['items'][0]['url']
            elif 'url' in data:
                direct_mp4_url = data['url']
                
            if not direct_mp4_url:
                print(f"🚨 API Structure Error: {data}")
                return None, None, None
                
            # Grab Metadata
            title = data.get('title', 'YouTube Video')
            thumbnails = data.get('thumbnails', [])
            thumbnail = thumbnails[-1]['url'] if thumbnails else ''
            
            # Download the MP4 directly to our server
            print("🚀 Downloading MP4 from API...")
            video_data = requests.get(direct_mp4_url).content
            with open(final_path, 'wb') as handler:
                handler.write(video_data)
                
            print("✅ API Download Complete!")
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