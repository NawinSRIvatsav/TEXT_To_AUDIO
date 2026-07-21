import os
from django.core.files.base import ContentFile
from .models import AudioConversion
from .services.video import generate_waveform_video, generate_captioned_video

def generate_video_task(conversion_id):
    """
    Background worker task to generate video for an AudioConversion clip.
    Queued via django-q to prevent frontend request timeouts.
    """
    try:
        conversion = AudioConversion.objects.get(pk=conversion_id)
        if not conversion.audio_file:
            print(f"Task Failed: Conversion {conversion_id} has no audio file.")
            return

        # Prepare paths
        audio_path = conversion.audio_file.path
        media_root = os.path.dirname(os.path.dirname(audio_path))
        videos_dir = os.path.join(media_root, 'videos')
        os.makedirs(videos_dir, exist_ok=True)

        temp_video_filename = f"video_{conversion.id}.mp4"
        temp_video_path = os.path.join(videos_dir, temp_video_filename)

        style = conversion.video_style or 'waveform'

        print(f"Generating video style: {style} for conversion {conversion_id}...")
        
        # Select video generator based on chosen style
        if style == 'captioned':
            generate_captioned_video(audio_path, temp_video_path)
        elif style == 'both':
            # Captioned video service includes both subtitles and waveforms!
            generate_captioned_video(audio_path, temp_video_path)
        else:
            # Default to waveform
            generate_waveform_video(audio_path, temp_video_path)

        # Verify video was generated
        if os.path.isfile(temp_video_path) and os.path.getsize(temp_video_path) > 0:
            with open(temp_video_path, 'rb') as f:
                # Save into Django FileField (automatically moves to media directory)
                conversion.video_file.save(temp_video_filename, ContentFile(f.read()))
            conversion.save()
            print(f"Video generated successfully for conversion {conversion_id}!")
            
            # Clean up temp file on disk (now stored in media storage)
            try:
                os.remove(temp_video_path)
            except OSError:
                pass
        else:
            print(f"Video file generation failed or output is empty for {conversion_id}.")
            
    except AudioConversion.DoesNotExist:
        print(f"Task Error: AudioConversion with ID {conversion_id} not found.")
    except Exception as e:
        print(f"Task Failed with exception: {str(e)}")


import io
from django.contrib.auth.models import User
from .models import GeneratedImage
from .services.image_gen import run_txt2img, run_img2img

def generate_image_task(user_id, prompt, style):
    """
    Background worker task to generate an image from prompt and style preset.
    Saves output locally under GeneratedImage model.
    """
    try:
        user = User.objects.get(pk=user_id) if user_id else None
        
        print(f"Generating image for prompt: '{prompt}' (style: {style})...")
        image = run_txt2img(prompt, style)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        gen_img = GeneratedImage(user=user, prompt=prompt, style=style)
        filename = f"gen_{style}.png"
        gen_img.image_file.save(filename, ContentFile(buffer.read()))
        gen_img.save()
        print(f"Image successfully generated and saved for user {user_id}!")
        
    except Exception as e:
        print(f"Image generation task failed: {str(e)}")

def generate_img2img_task(user_id, prompt, init_image_bytes, strength, style):
    """
    Background worker task to stylize/edit an image using image-to-image pipeline.
    """
    try:
        user = User.objects.get(pk=user_id) if user_id else None
        
        print(f"Stylizing image for prompt: '{prompt}' (style: {style})...")
        image = run_img2img(prompt, init_image_bytes, strength=strength, style_preset=style)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        gen_img = GeneratedImage(user=user, prompt=prompt, style=style)
        filename = f"stylized_{style}.png"
        gen_img.image_file.save(filename, ContentFile(buffer.read()))
        gen_img.save()
        print(f"Image stylization successfully saved for user {user_id}!")
        
    except Exception as e:
        print(f"Image stylization task failed: {str(e)}")

from .services.image_gen import run_inpaint

def generate_inpaint_task(user_id, prompt, init_image_bytes, mask_image_bytes, style):
    """
    Background worker task to edit/inpaint an image using Stable Diffusion inpainting.
    """
    try:
        user = User.objects.get(pk=user_id) if user_id else None
        
        print(f"Inpainting image for prompt: '{prompt}'...")
        image = run_inpaint(prompt, init_image_bytes, mask_image_bytes, style_preset=style)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        gen_img = GeneratedImage(user=user, prompt=prompt, style=style)
        filename = f"inpainted_{style}.png"
        gen_img.image_file.save(filename, ContentFile(buffer.read()))
        gen_img.save()
        print(f"Image inpainting successfully saved for user {user_id}!")
        
    except Exception as e:
        print(f"Image inpainting task failed: {str(e)}")
