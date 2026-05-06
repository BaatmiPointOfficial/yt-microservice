import os
import requests
import time

def download_youtube_video(video_url, quality="720p"):
    """
    Bypasses bot protection using the official Cobalt API with strict v7 Headers.
    """
    clean_url = video_url.strip()
    print(f"🚀 Extracting Media: {clean_url}")
    
    api_endpoints = [
        "https://api.cobalt.tools/",             
        "https://cobalt-api.kwiatektv.com/",     
        "https://api.cobalt.tools/api/json"      
    ]
    
    # 🌟 FIX 1: Add the Disguise Headers back! Cobalt strictly requires these now.
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://cobalt.tools",
        "Referer": "https://cobalt.tools/"
    }
    
    # 🌟 FIX 2: Strict Payload. No legacy/extra parameters allowed.
    payload = { "url": clean_url }
    if quality == "audio":
        payload["downloadMode"] = "audio"
    elif quality == "best":
        payload["videoQuality"] = "max"
    else:
        payload["videoQuality"] = "720" if quality == "720p" else "480"

    data = None
    
    # The Failover Loop
    for api_url in api_endpoints:
        print(f"📡 Attempting connection to: {api_url}")
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") != "error":
                    print(f"✅ Connected successfully to {api_url}")
                    break 
            else:
                print(f"⚠️ {api_url} returned status {response.status_code}")
                # Print the exact error so you can see it in Render!
                print(f"🔍 Server Said: {response.text}")
        except Exception as e:
            print(f"⚠️ {api_url} is offline or blocked. Switching to backup...")
            continue

    if not data or data.get("status") == "error":
        error_text = data.get('text', 'Unknown Error') if data else 'All API servers offline or rejected the request.'
        print(f"❌ Extraction Failed: {error_text}")
        return None, None, None

    direct_download_url = data.get("url")
    
    if not direct_download_url:
        print("❌ Server did not return a valid download link.")
        return None, None, None

    timestamp = int(time.time())
    ext = "mp3" if quality == "audio" else "mp4"
    safe_filename = f"vaniconnect_media_{timestamp}.{ext}"
    output_path = os.path.join("downloads", safe_filename)

    print("📥 Bypassed protection! Downloading file to Render...")
    
    try:
        file_response = requests.get(direct_download_url, stream=True, timeout=30)
        with open(output_path, "wb") as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"✅ Success! Media saved as {safe_filename}")
        return safe_filename, "VaniConnect Media", "https://via.placeholder.com/640x360.png?text=Media+Ready"
        
    except Exception as e:
        print(f"🚨 Render Download Error: {e}")
        return None, None, None