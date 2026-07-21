import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import AudioConversion, GeneratedImage

@receiver(post_delete, sender=AudioConversion)
def auto_delete_file_on_delete_conversion(sender, instance, **kwargs):
    """Deletes audio and video files from filesystem when AudioConversion object is deleted."""
    if instance.audio_file:
        if os.path.isfile(instance.audio_file.path):
            try:
                os.remove(instance.audio_file.path)
            except OSError:
                pass
                
    if hasattr(instance, 'video_file') and instance.video_file:
        try:
            if os.path.isfile(instance.video_file.path):
                os.remove(instance.video_file.path)
        except (OSError, ValueError):
            pass

@receiver(post_delete, sender=GeneratedImage)
def auto_delete_file_on_delete_image(sender, instance, **kwargs):
    """Deletes image file from filesystem when GeneratedImage object is deleted."""
    if instance.image_file:
        try:
            if os.path.isfile(instance.image_file.path):
                os.remove(instance.image_file.path)
        except (OSError, ValueError):
            pass
