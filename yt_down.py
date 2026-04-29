import os
import requests
import time

def download_youtube_video(video_url, quality="720p"):
    """
    Bypasses YouTube's bot protection using the Cobalt V7 API.
    Returns: (safe_filename, title, thumbnail)
    """
    print(f"🚀 Asking Cobalt V7 API to extract: {video_url}")
    
    # 🌟 THE V7 FIX: New Endpoint
    api_url = "https://api.cobalt.tools/"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    # 🌟 THE V7 FIX: New Payload Rules
    payload = {
        "url": video_url,
        "videoQuality": "720",
        "downloadMode": "audio" if quality == "audio" else "auto"
    }

    try:
        # Send the request to Cobalt
        response = requests.post(api_url, json=payload, headers=headers)
        
        # Stop the exact crash you just got if Cobalt sends HTML instead of JSON
        if response.status_code != 200:
            print(f"❌ Cobalt Server Error: {response.status_code}")
            return None, None, None

        data = response.json()

        if data.get("status") == "error":
            print(f"❌ Cobalt Error: {data.get('text', 'Unknown Error')}")
            return None, None, None

        # Cobalt gives us a clean, unblocked direct download link!
        direct_download_url = data.get("url")
        
        if not direct_download_url:
            print("❌ Cobalt did not return a valid direct link.")
            return None, None, None

        # 2. Download the actual file from Cobalt's clean link
        timestamp = int(time.time())
        ext = "mp3" if quality == "audio" else "mp4"
        safe_filename = f"yt_bypass_{timestamp}.{ext}"
        output_path = os.path.join("downloads", safe_filename)

        print("📥 Bypassed! Downloading file from Cobalt to Render...")
        
        # Stream the download so we don't crash Render's RAM
        file_response = requests.get(direct_download_url, stream=True)
        with open(output_path, "wb") as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ Success! Video saved as {safe_filename}")
        
        return safe_filename, "YouTube Video", "https://via.placeholder.com/640x360.png?text=Video+Ready"

    except Exception as e:
        print(f"🚨 Python Error in Downloader: {e}")
        return None, None, None