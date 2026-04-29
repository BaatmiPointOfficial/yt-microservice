import os
import requests
import time

def download_youtube_video(video_url, quality="720p"):
    """
    Bypasses YouTube's bot protection using the Cobalt API.
    Returns: (safe_filename, title, thumbnail)
    """
    print(f"🚀 Asking Cobalt API to extract: {video_url}")
    
    # 1. Ask Cobalt to do the hard work and bypass YouTube
    api_url = "https://api.cobalt.tools/api/json"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Tell Cobalt exactly what we want
    payload = {
        "url": video_url,
        "vQuality": "720" if quality != "audio" else "max",
        "isAudioOnly": quality == "audio"
    }

    try:
        # Send the request to Cobalt
        response = requests.post(api_url, json=payload, headers=headers)
        data = response.json()

        if response.status_code != 200 or data.get("status") == "error":
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