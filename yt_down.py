import yt_dlp
import os

def download_youtube_video(video_url, output_folder="downloads", quality="720p"):
    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        ydl_opts = {
            # 'best' grabs the pre-glued video+audio file. No ffmpeg needed! 🚀
            'format': 'best', 
            'outtmpl': f'{output_folder}/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'quiet': False
        }

        print(f"Starting yt-dlp download for: {video_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            return os.path.basename(filename)

    except Exception as e:
        # If it ever crashes again, it will scream the exact reason into the logs!
        print(f"🚨 YT-DLP CRASHED: {e}")
        return None