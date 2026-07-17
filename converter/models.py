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

    def delete(self, *args, **kwargs):
        if self.audio_file:
            if os.path.isfile(self.audio_file.path):
                try:
                    os.remove(self.audio_file.path)
                except OSError:
                    pass
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.voice})"

