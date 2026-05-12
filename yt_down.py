import os
import requests
import time
import re

def extract_video_id(url):
    """Extracts the exact 11-character video ID from any YouTube/Shorts link"""
    match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def download_youtube_video(video_url, quality="720p"):
    """
    The Piped API Engine. 
    Bypasses yt-dlp and Cobalt entirely by querying the open-source Piped network.
    """
    print(f"🚀 Using Piped Open-Source Network for: {video_url}")

    video_id = extract_video_id(video_url)
    if not video_id:
        print("❌ Could not extract YouTube Video ID.")
        return None, None, None

    # Hitting the primary, highly-stable Piped API instance
    piped_api = f"https://pipedapi.kavin.rocks/streams/{video_id}"

    try:
        # 1. Ask Piped for the raw video stream data
        response = requests.get(piped_api, timeout=15)
        if response.status_code != 200:
            print(f"❌ Piped API rejected the request. Status: {response.status_code}")
            return None, None, None

        data = response.json()
        video_streams = data.get("videoStreams", [])

        if not video_streams:
            print("❌ No video streams found on Piped.")
            return None, None, None

        # 2. Find a combined Audio+Video MP4 stream (Usually 720p or 360p)
        direct_url = None
        for stream in video_streams:
            # We want an MP4 file that is NOT just video-only (needs audio included)
            if stream.get("format") == "MPEG_4" and stream.get("videoOnly") is False:
                direct_url = stream.get("url")
                # If we find 720p, lock it in and break the loop. Otherwise, keep the first one found.
                if stream.get("quality") == "720p":
                    break

        if not direct_url:
            print("❌ No combined MP4 format available on this video.")
            return None, None, None

        # 3. Download the raw file directly to Render
        timestamp = int(time.time())
        safe_filename = f"vaniconnect_{timestamp}.mp4"
        output_path = os.path.join("downloads", safe_filename)

        if not os.path.exists("downloads"):
            os.makedirs("downloads")

        print("📥 Raw stream found! Downloading directly to Render...")
        file_response = requests.get(direct_url, stream=True, timeout=60)
        
        with open(output_path, "wb") as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)

        title = data.get("title", "VaniConnect Video")
        thumbnail = data.get("thumbnailUrl", "https://via.placeholder.com/640")

        print(f"✅ Success! Saved natively as {safe_filename}")
        return safe_filename, title, thumbnail

    except Exception as e:
        print(f"🚨 Engine Error: {e}")
        return None, None, None