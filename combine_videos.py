from moviepy import VideoFileClip, concatenate_videoclips
import os

def combine_videos():
    try:
        video1_path = "1.mp4"
        video2_path = "2.mp4"
        output_path = "video_combinado.mp4"

        if not os.path.exists(video1_path):
            print(f"Error: {video1_path} not found.")
            return

        if not os.path.exists(video2_path):
            print(f"Error: {video2_path} not found.")
            return

        clip1 = VideoFileClip(video1_path)
        clip2 = VideoFileClip(video2_path)
        
        # Resize clip2 to match clip1's size if needed, or handle aspect ratio
        if clip1.size != clip2.size:
             print(f"Resizing clip2 from {clip2.size} to {clip1.size}...")
             clip2 = clip2.resize(clip1.size)

        final_clip = concatenate_videoclips([clip1, clip2])
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        print(f"Video combined successfully: {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    combine_videos()
