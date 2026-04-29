import os
import requests
import time

def download_youtube_video(video_url, quality="720p"):
    """
    Bypasses YouTube's bot protection using the Cobalt API.
    Returns: (safe_filename, title, thumbnail)
    """
    # 🧹 Clean the URL to remove any hidden spaces sent from the frontend
    clean_url = video_url.strip()
    print(f"🚀 Asking Cobalt API to extract: {clean_url}")
    
    api_url = "https://api.cobalt.tools/"
    
    # 🛡️ Disguise our server as a normal web browser
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://cobalt.tools",
        "Referer": "https://cobalt.tools/"
    }
    
    # 🌟 MINIMAL PAYLOAD: We only send exactly what is necessary.
    payload = {
        "url": clean_url
    }
    
    if quality == "audio":
        payload["downloadMode"] = "audio"
    else:
        payload["videoQuality"] = "720"

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        
        # 🕵️‍♂️ THE X-RAY: If it fails, read the actual error message!
        if response.status_code != 200:
            print(f"❌ Cobalt Server Error: {response.status_code}")
            try:
                error_details = response.json()
                print(f"🔍 Cobalt Says: {error_details}")
            except:
                print(f"🔍 Cobalt Raw Error: {response.text}")
            return None, None, None

        data = response.json()

        if data.get("status") == "error":
            print(f"❌ Cobalt Error: {data.get('text', 'Unknown Error')}")
            return None, None, None

        direct_download_url = data.get("url")
        
        if not direct_download_url:
            print("❌ Cobalt did not return a valid direct link.")
            return None, None, None

        timestamp = int(time.time())
        ext = "mp3" if quality == "audio" else "mp4"
        safe_filename = f"yt_bypass_{timestamp}.{ext}"
        output_path = os.path.join("downloads", safe_filename)

        print("📥 Bypassed! Downloading file from Cobalt to Render...")
        
        file_response = requests.get(direct_download_url, stream=True)
        with open(output_path, "wb") as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ Success! Video saved as {safe_filename}")
        
        return safe_filename, "YouTube Video", "https://via.placeholder.com/640x360.png?text=Video+Ready"

    except Exception as e:
        print(f"🚨 Python Error in Downloader: {e}")
        return None, None, None