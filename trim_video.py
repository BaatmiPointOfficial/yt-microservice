from moviepy.editor import VideoFileClip
import cv2
import os
import zipfile  # Needed for packing the batch clips
import math     # Needed to calculate how many clips to make
import subprocess # ⚡ Needed for instant stream-copying and ultra-lightweight metadata reads

def trim_video(input_path, output_path, start_sec, end_sec):
    """ Cuts the video to the specified time range. """
    try:
        video = VideoFileClip(input_path)
        new_video = video.subclip(start_sec, end_sec)
        
        new_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast", 
            threads=8, 
            logger=None
        )
        
        video.close()
        new_video.close()
        return True
    except Exception as e:
        print(f"Trim Error: {e}")
        return False

def add_professional_text(input_path, output_path, text="VaniConnect AI"):
    """ Adds a professional text overlay using OpenCV. """
    try:
        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        temp_v = "downloads/temp_text.mp4" 
        out = cv2.VideoWriter(temp_v, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

        while True:
            ret, frame = cap.read()
            if not ret: break
            
            cv2.putText(frame, text, (52, height - 48), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 0), 3)
            cv2.putText(frame, text, (50, height - 50), cv2.FONT_HERSHEY_DUPLEX, 1.5, (255, 255, 255), 2)
            out.write(frame)
            
        cap.release()
        out.release()

        original = VideoFileClip(input_path)
        processed = VideoFileClip(temp_v)
        
        if original.audio is not None:
            final = processed.set_audio(original.audio)
        else:
            final = processed

        final.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast", 
            threads=8, 
            logger=None
        )
        
        original.close()
        processed.close()
        final.close()
        
        os.remove(temp_v)
        return True
    except Exception as e:
        print(f"Text Overlay Error: {e}")
        return False

# ==========================================
# 🌟 PRO TIER FEATURE: THE BATCH SPLITTER (RAM OPTIMIZED)
# ==========================================
def split_video_into_parts(video_path, clip_duration_sec, output_folder):
    """ Slices a long video into multiple equal parts safely using pure system binaries. """
    try:
        # ⚡ PURE FFPROBE: Read total duration from file headers without loading video bytes into Python RAM!
        cmd_duration = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nocrepan=1', video_path
        ]
        result = subprocess.run(cmd_duration, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        total_duration = float(result.stdout.strip())
        
        # Calculate how many full clips we get
        number_of_clips = math.ceil(total_duration / clip_duration_sec)
        
        saved_files = []
        base_name = os.path.basename(video_path).rsplit('.', 1)[0]
        
        os.makedirs(output_folder, exist_ok=True)

        for i in range(number_of_clips):
            start_time = i * clip_duration_sec
            end_time = min((i + 1) * clip_duration_sec, total_duration)
            duration_to_cut = end_time - start_time
            
            # Skip tiny artifacts at the absolute tail end
            if duration_to_cut < 3:
                continue
                
            out_name = os.path.join(output_folder, f"{base_name}_part{i+1}.mp4")
            print(f"✂️ Instant Slicing Part {i+1}: {start_time}s to {end_time}s")
            
            # Use native stream copying (-c copy) to slice file blocks instantaneously
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration_to_cut),
                '-c', 'copy',
                out_name
            ]
            
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if os.path.exists(out_name):
                saved_files.append(out_name)
        
        # 📦 Zip up files cleanly
        zip_filename = os.path.join(output_folder, f"{base_name}_Batch.zip")
        print("📦 Zipping files together...")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in saved_files:
                zipf.write(file, os.path.basename(file))
                os.remove(file) # Delete separate parts to keep your Render storage empty
                
        return True, zip_filename
    except Exception as e:
        print(f"🚨 Batch Split Error: {e}")
        return False, None