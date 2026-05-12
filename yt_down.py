import os
import requests
import time

def download_youtube_video(video_url, quality="720p"):
    """
    The 'Hydra' Engine for YouTube.
    Bypasses YouTube's Bot blocks by routing through the Cobalt Community Network.
    """
    print(f"🚀 Asking Cobalt Network to fetch YouTube video: {video_url}")

    # The Hydra array: Community servers that handle YouTube's anti-bot security for us
    cobalt_servers = [
        "https://cobalt.omkr.in/api/json",
        "https://cobalt.canine.ly/api/json",
        "https://cobalt.shovit.dev/api/json"
    ]

    payload = {"url": video_url.strip()}
    if quality == "audio": 
        payload["isAudioOnly"] = True
    else: 
        payload["videoQuality"] = "720"

    direct_download_url = None

    # 1. Ask the network for the unblocked video link
    for api_url in cobalt_servers:
        domain = "/".join(api_url.split("/")[:3])
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Origin": domain,
            "Referer": domain + "/"
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") != "error" and data.get("url"):
                    direct_download_url = data.get("url")
                    print(f"✅ Success! {domain} bypassed YouTube's security.")
                    break
        except Exception:
            print(f"⚠️ Server {domain} timeout. Pivoting to next...")
            continue

    if not direct_download_url:
        print("❌ All community servers are currently busy.")
        return None, None, None

    # 2. Download the video directly to Render
    timestamp = int(time.time())
    ext = "mp3" if quality == "audio" else "mp4"
    safe_filename = f"vaniconnect_{timestamp}.{ext}"
    
    output_path = os.path.join("downloads", safe_filename)
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    print("📥 Downloading media to Render storage...")
    try:
        file_response = requests.get(direct_download_url, stream=True, timeout=30)
        with open(output_path, "wb") as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ Download Complete! Saved natively as {safe_filename}")
        return safe_filename, "VaniConnect Media", "https://via.placeholder.com/640x360.png?text=Media+Ready"
    except Exception as e:
        print(f"🚨 Download writing error: {e}")
        return None, None, None