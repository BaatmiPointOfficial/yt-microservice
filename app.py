from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_down
import os
import boto3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('R2_SECRET_KEY')
)
bucket_name = os.getenv('R2_BUCKET_NAME')

@app.get("/")
def read_root():
    return {"status": "YouTube Microservice is LIVE! 🚀"}

@app.post("/api/youtube-downloader")
async def process_youtube(url: str = Form(...), quality: str = Form("720p")):
    print(f"📥 Received request for YouTube video: {url}")
    
    try:
        # 1. Download the video
        safe_filename = yt_down.download_youtube_video(video_url=url, output_folder="downloads", quality=quality)
        
        if not safe_filename:
            print("🚨 yt_down returned None! The download failed.")
            return JSONResponse(status_code=500, content={"error": "Failed to download video"})
            
        file_path = os.path.join("downloads", safe_filename)
        
        # 2. Upload to Cloudflare
        print(f"☁️ Uploading {safe_filename} to Cloudflare...")
        with open(file_path, 'rb') as video_file:
            s3.put_object(Bucket=bucket_name, Key=f'downloads/{safe_filename}', Body=video_file)
            
        os.remove(file_path) 
        print("✅ Upload complete! Sending link to website.")
        
        return {"message": "Success!", "file_name": safe_filename, "url": f"/downloads/{safe_filename}"}
        
    except Exception as e:
        print(f"🚨 MAJOR SERVER ERROR: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})