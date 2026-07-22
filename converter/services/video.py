import os
import cv2
import numpy as np
import whisper
from moviepy import VideoClip, AudioFileClip

_whisper_model = None

def get_whisper_model():
    """Initializes and returns cached Whisper model locally (uses 'tiny' for fast execution)."""
    global _whisper_model
    if _whisper_model is None:
        # Downloads model on first run locally (~72MB)
        _whisper_model = whisper.load_model("tiny")
    return _whisper_model

def get_active_caption(t, segments):
    """Finds the subtitle text corresponding to timestamp t."""
    for seg in segments:
        if seg['start'] <= t <= seg['end']:
            return seg['text'].strip()
    return ""

def draw_caption_with_wrap(frame, text, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.7, color=(255, 255, 255), thickness=2, max_width=580):
    """Draws captioned text centered at the bottom of the frame with wrapping."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        size = cv2.getTextSize(test_line, font, font_scale, thickness)[0]
        if size[0] > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    # Render lines starting from bottom upwards
    y_offset = 420
    for line in reversed(lines):
        size = cv2.getTextSize(line, font, font_scale, thickness)[0]
        x = (640 - size[0]) // 2
        
        # Draw background bubble
        cv2.rectangle(
            frame, 
            (x - 8, y_offset - size[1] - 8), 
            (x + size[0] + 8, y_offset + 6), 
            (15, 12, 30), 
            -1
        )
        # Draw text
        cv2.putText(frame, line, (x, y_offset), font, font_scale, color, thickness, cv2.LINE_AA)
        y_offset -= (size[1] + 15)

def generate_waveform_video(audio_path, output_path, background="solid", background_path=None):
    """
    Renders animated waveform bars synced to the audio over a solid color or background image.
    Uses MoviePy and OpenCV for rendering without ImageMagick dependencies.
    """
    audio = AudioFileClip(audio_path)
    duration = audio.duration
    
    # Load background image if provided and exists
    bg_img = None
    if background == "image" and background_path and os.path.isfile(background_path):
        bg_img = cv2.imread(background_path)
        if bg_img is not None:
            bg_img = cv2.resize(bg_img, (640, 480))

    def make_frame(t):
        if bg_img is not None:
            frame = bg_img.copy()
        else:
            # Solid dark background (BGR format: #141125 -> (37, 17, 20))
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (37, 17, 20)

        # Draw floating grid lines in the background
        for y in range(0, 480, 40):
            cv2.line(frame, (0, y), (640, y), (30, 25, 45), 1)

        # Get audio volume/amplitude at time t
        try:
            amplitude = np.mean(np.abs(audio.get_frame(t)))
        except Exception:
            amplitude = 0.05

        # Draw animated sound wave bars
        num_bars = 28
        bar_width = 12
        gap = 6
        start_x = (640 - (num_bars * (bar_width + gap) - gap)) // 2
        
        for i in range(num_bars):
            # Calculate organic wave heights
            factor = np.sin(t * 8 + i * 0.4) * 0.4 + 0.6
            height = int(amplitude * 400 * factor)
            height = max(8, min(180, height))
            
            x = start_x + i * (bar_width + gap)
            y1 = 240 - height
            y2 = 240 + height
            
            # Drawing neon cyan-purple gradients
            cv2.rectangle(frame, (x, y1), (x + bar_width, y2), (247, 85, 168), -1) # BGR: Purple
            cv2.rectangle(frame, (x + 2, y1 + 2), (x + bar_width - 2, y2 - 2), (212, 182, 6), 1) # BGR: Cyan border

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_audio(audio)
    
    # Output to target path
    clip.write_videofile(
        output_path, 
        fps=15, 
        codec='libx264', 
        audio_codec='aac', 
        verbose=False, 
        logger=None
    )
    
    clip.close()
    audio.close()
    return output_path

def generate_captioned_video(audio_path, output_path, background_path=None):
    """
    Transcribes audio using local Whisper and burns captions into the video,
    synced to the audio track.
    """
    # 1. Transcribe audio locally using Whisper
    model = get_whisper_model()
    result = model.transcribe(audio_path)
    segments = result.get('segments', [])

    audio = AudioFileClip(audio_path)
    duration = audio.duration

    bg_img = None
    if background_path and os.path.isfile(background_path):
        bg_img = cv2.imread(background_path)
        if bg_img is not None:
            bg_img = cv2.resize(bg_img, (640, 480))

    def make_frame(t):
        if bg_img is not None:
            frame = bg_img.copy()
        else:
            # Solid dark BGR frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (37, 17, 20)

        # Get audio volume/amplitude at time t
        try:
            amplitude = np.mean(np.abs(audio.get_frame(t)))
        except Exception:
            amplitude = 0.05

        # Draw bouncing sound waves (positioned at the upper region to leave room for text)
        num_bars = 20
        bar_width = 8
        gap = 4
        start_x = (640 - (num_bars * (bar_width + gap) - gap)) // 2
        
        for i in range(num_bars):
            factor = np.cos(t * 6 + i * 0.3) * 0.3 + 0.7
            height = int(amplitude * 200 * factor)
            height = max(5, min(100, height))
            
            x = start_x + i * (bar_width + gap)
            y1 = 150 - height
            y2 = 150 + height
            cv2.rectangle(frame, (x, y1), (x + bar_width, y2), (168, 85, 247), -1)

        # Find active caption at timestamp t
        caption = get_active_caption(t, segments)
        if caption:
            draw_caption_with_wrap(frame, caption)

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_audio(audio)
    
    # Write captioned video
    clip.write_videofile(
        output_path, 
        fps=15, 
        codec='libx264', 
        audio_codec='aac', 
        verbose=False, 
        logger=None
    )
    
    clip.close()
    audio.close()
    return output_path
