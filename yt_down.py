import os
import requests
import time

def download_youtube_video(video_url, quality="720p"):
    """
    Bypasses bot protection using the official Cobalt API with built-in Failover Servers.
    """
    clean_url = video_url.strip()
    print(f"🚀 Extracting Media: {clean_url}")
    
    # 🌟 THE FIX: A list of active Cobalt instances. If one dies, it tries the next!
    api_endpoints = [
        "https://api.cobalt.tools/",             # The Official Main Server
        "https://cobalt-api.kwiatektv.com/",     # Backup 1
        "https://api.cobalt.tools/api/json"      # Legacy Endpoint Backup
    ]
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    # The Cobalt payload mapping
    payload = { "url": clean_url }
    if quality == "audio":
        payload["downloadMode"] = "audio"
        payload["isAudioOnly"] = True # Sending both for backward API compatibility
    elif quality == "best":
        payload["videoQuality"] = "max"
    else:
        payload["videoQuality"] = "720" if quality == "720p" else "480"

    data = None
    
    # 🛡️ THE FAILOVER LOOP
    for api_url in api_endpoints:
        print(f"📡 Attempting connection to: {api_url}")
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") != "error":
                    print(f"✅ Connected successfully to {api_url}")
                    break # Stop looking, we found a working server!
            else:
                print(f"⚠️ {api_url} returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️ {api_url} is offline or blocked. Switching to backup...")
            continue

    # If the loop finishes and data is still None, all servers are down
    if not data or data.get("status") == "error":
        error_text = data.get('text', 'Unknown Error') if data else 'All API servers offline'
        print(f"❌ Extraction Failed: {error_text}")
        return None, None, None

    direct_download_url = data.get("url")
    
    if not direct_download_url:
        print("❌ Server did not return a valid download link.")
        return None, None, None

    # Proceed with saving the file to Render
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