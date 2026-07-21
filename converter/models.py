from django.db import models
from django.contrib.auth.models import User
import os

class AudioConversion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='conversions')
    title = models.CharField(max_length=255)
    original_text = models.TextField()
    language = models.CharField(max_length=50, default='en')
    voice = models.CharField(max_length=100, default='en-US-AriaNeural')
    speed = models.CharField(max_length=10, default='normal') # 'normal' or 'slow'
    audio_file = models.FileField(upload_to='audio_conversions/')
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Feature 1: Translation fields
    source_language = models.CharField(max_length=50, default='auto')
    translated_text = models.TextField(blank=True, null=True)
    was_translated = models.BooleanField(default=False)

    # Feature 4: Audio-to-Video fields
    video_file = models.FileField(upload_to='videos/', blank=True, null=True)
    video_style = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        choices=[
            ("waveform", "Waveform Only"),
            ("captioned", "Captioned Only"),
            ("both", "Both Waveform & Captions")
        ]
    )

    def __str__(self):
        return f"{self.title} ({self.voice})"


class GeneratedImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='generated_images')
    prompt = models.TextField()
    style = models.CharField(max_length=50, default='realistic')
    image_file = models.ImageField(upload_to='generated_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image: {self.prompt[:30]} ({self.style})"

