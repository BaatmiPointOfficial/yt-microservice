from moviepy.editor import VideoFileClip
import cv2
import os
import zipfile  # 🌟 NEW: Needed for packing the batch clips
import math     # 🌟 NEW: Needed to calculate how many clips to make

def trim_video(input_path, output_path, start_sec, end_sec):
    """ Cuts the video to the specified time range. """
    try:
        # Load the video and explicitly grab the audio
        video = VideoFileClip(input_path)
        new_video = video.subclip(start_sec, end_sec)
        
        new_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", # 🌐 Force Web-Safe Audio
            preset="ultrafast", 
            threads=8, 
            logger=None
        )
        
        # 🛑 WINDOWS FIX: Explicitly close everything to free RAM!
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
            
            # Add text with a subtle shadow for readability
            cv2.putText(frame, text, (52, height - 48), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 0), 3)
            cv2.putText(frame, text, (50, height - 50), cv2.FONT_HERSHEY_DUPLEX, 1.5, (255, 255, 255), 2)
            out.write(frame)
            
        cap.release()
        out.release()

        # 🔊 THE AUDIO FIX: Explicitly rip the audio and force it onto the new video
        original = VideoFileClip(input_path)
        processed = VideoFileClip(temp_v)
        
        # Only set audio if the original video actually had sound!
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
        
        # 🛑 WINDOWS FIX: Explicitly close every single file!
        original.close()
        processed.close()
        final.close()
        
        os.remove(temp_v)
        return True
    except Exception as e:
        print(f"Text Overlay Error: {e}")
        return False

# ==========================================
# 🌟 PRO TIER FEATURE: THE BATCH SPLITTER
# ==========================================
def split_video_into_parts(video_path, clip_duration_sec, output_folder):
    """ Slices a long video into multiple equal parts and zips them up. """
    try:
        video = VideoFileClip(video_path)
        total_duration = video.duration
        
        # Calculate how many full clips we get
        number_of_clips = math.ceil(total_duration / clip_duration_sec)
        
        saved_files = []
        base_name = os.path.basename(video_path).rsplit('.', 1)[0]

        for i in range(number_of_clips):
            start_time = i * clip_duration_sec
            end_time = min((i + 1) * clip_duration_sec, total_duration)
            
            # Skip tiny clips at the very end (less than 3 seconds)
            if end_time - start_time < 3:
                continue
                
            out_name = os.path.join(output_folder, f"{base_name}_part{i+1}.mp4")
            
            # Slice and save with turbo settings
            clip = video.subclip(start_time, end_time)
            print(f"✂️ Cutting Part {i+1}: {start_time}s to {end_time}s")
            
            clip.write_videofile(
                out_name, 
                codec="libx264", 
                audio_codec="aac", 
                preset="ultrafast", 
                threads=4, 
                logger=None
            )
            saved_files.append(out_name)
        
        video.close()
        
        # 📦 Zip them all up!
        zip_filename = os.path.join(output_folder, f"{base_name}_Batch.zip")
        print("📦 Zipping files together...")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in saved_files:
                zipf.write(file, os.path.basename(file))
                os.remove(file) # Delete the individual MP4s to save space
                
        return True, zip_filename
    except Exception as e:
        print(f"🚨 Batch Split Error: {e}")
        return False, None