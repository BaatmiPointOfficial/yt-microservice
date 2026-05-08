import os
import requests
import time

def download_universal_media(video_url, quality="720p"):
    """
    Directly hits the public Cobalt API. No RapidAPI. No Cookies. No Credit Cards.
    """
    print(f"🚀 Asking Official Cobalt API to extract: {video_url}")

    api_url = "https://api.cobalt.tools/api/json"

    # 🛡️ THE VIP HEADERS: These exact 5 lines stop Cloudflare from blocking your Render server
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://cobalt.tools",
        "Referer": "https://cobalt.tools/"
    }

    # Clean the URL to prevent weird formatting errors
    payload = {
        "url": video_url.strip(),
    }
    
    if quality == "audio":
        payload["isAudioOnly"] = True
    else:
        payload["videoQuality"] = "720"

    try:
        # 1. Ask Cobalt for the direct video link
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"❌ Cobalt Blocked it. Status: {response.status_code}")
            print(f"🔍 Server Response: {response.text}")
            return None, None, None

        data = response.json()
        
        if data.get("status") == "error":
            print(f"❌ Cobalt Extraction Error: {data.get('text')}")
            return None, None, None
            
        direct_download_url = data.get("url")

        if not direct_download_url:
            print("❌ Cobalt didn't find a valid video link.")
            return None, None, None

        # 2. Download the unblocked video directly to your Render Server
        timestamp = int(time.time())
        ext = "mp3" if quality == "audio" else "mp4"
        safe_filename = f"vaniconnect_{timestamp}.{ext}"
        
        output_path = os.path.join("downloads", safe_filename)
        
        # Ensure the folder exists
        if not os.path.exists("downloads"):
            os.makedirs("downloads")

        print("📥 Bypassed Meta! Downloading media to Render...")
        file_response = requests.get(direct_download_url, stream=True, timeout=30)
        
        with open(output_path, "wb") as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ Success! Saved natively as {safe_filename}")
        return safe_filename, "VaniConnect Media", "https://via.placeholder.com/640x360.png?text=Media+Ready"

    except Exception as e:
        print(f"🚨 Python Error: {str(e)}")
        return None, None, None