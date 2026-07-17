from django import forms
from django.core.exceptions import ValidationError
from .models import AudioConversion

LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('de', 'German'),
    ('hi', 'Hindi'),
]

VOICE_MAP = {
    'en': [
        ('en-US-AriaNeural', 'US - Aria (Female)'),
        ('en-US-GuyNeural', 'US - Guy (Male)'),
        ('en-US-JennyNeural', 'US - Jenny (Female)'),
        ('en-GB-SoniaNeural', 'UK - Sonia (Female)'),
        ('en-GB-RyanNeural', 'UK - Ryan (Male)'),
        ('en-IN-NeerjaNeural', 'India - Neerja (Female)'),
        ('en-IN-PrabhatNeural', 'India - Prabhat (Male)'),
        ('en-AU-NatashaNeural', 'Australia - Natasha (Female)'),
        ('en-AU-WilliamNeural', 'Australia - William (Male)'),
    ],
    'es': [
        ('es-ES-ElviraNeural', 'Spain - Elvira (Female)'),
        ('es-ES-AlvaroNeural', 'Spain - Alvaro (Male)'),
        ('es-US-PalomaNeural', 'US - Paloma (Female)'),
        ('es-US-AlonsoNeural', 'US - Alonso (Male)'),
    ],
    'fr': [
        ('fr-FR-DeniseNeural', 'France - Denise (Female)'),
        ('fr-FR-HenriNeural', 'France - Henri (Male)'),
    ],
    'de': [
        ('de-DE-KatjaNeural', 'Germany - Katja (Female)'),
        ('de-DE-KillianNeural', 'Germany - Killian (Male)'),
    ],
    'hi': [
        ('hi-IN-SwaraNeural', 'India - Swara (Female)'),
        ('hi-IN-MadhurNeural', 'India - Madhur (Male)'),
    ],
}

ALL_VOICE_CHOICES = []
for lang, voices in VOICE_MAP.items():
    ALL_VOICE_CHOICES.extend(voices)

SPEED_CHOICES = [
    ('normal', 'Normal Speed'),
    ('slow', 'Slow Speed'),
]

class AudioConversionForm(forms.ModelForm):
    text = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter text to convert to audio...',
            'rows': 8,
            'class': 'form-control glass-input'
        }),
        required=False
    )
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'accept': '.pdf,.txt',
            'class': 'form-control glass-file-input'
        }),
        required=False
    )

    class Meta:
        model = AudioConversion
        fields = ['title', 'language', 'voice', 'speed']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Give this audio a name...',
                'class': 'form-control glass-input'
            }),
            'language': forms.Select(choices=LANGUAGE_CHOICES, attrs={'class': 'form-control glass-select', 'onchange': 'updateVoiceDropdown()'}),
            'voice': forms.Select(choices=ALL_VOICE_CHOICES, attrs={'class': 'form-control glass-select'}),
            'speed': forms.Select(choices=SPEED_CHOICES, attrs={'class': 'form-control glass-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        text = cleaned_data.get('text')
        file = cleaned_data.get('file')

        if not text and not file:
            raise ValidationError("You must provide either text or upload a file.")

        # File validation
        if file:
            extension = file.name.split('.')[-1].lower()
            if extension not in ['txt', 'pdf']:
                raise ValidationError("Only .txt and .pdf files are supported.")

        return cleaned_data
