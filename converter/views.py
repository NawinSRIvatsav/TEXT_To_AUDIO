from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum, Q
from django.core.files.base import ContentFile
from django.contrib import messages
from django.http import JsonResponse

from PyPDF2 import PdfReader
import io
import datetime

from .models import AudioConversion
from .forms import AudioConversionForm

def home(request):
    """Home view redirecting to dashboard if logged in, otherwise to convert page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('convert')

def convert_view(request):
    """Main view handling the conversion of text/files to audio."""
    if request.method == 'POST':
        form = AudioConversionForm(request.POST, request.FILES)
        if form.is_valid():
            text = form.cleaned_data.get('text', '')
            uploaded_file = form.cleaned_data.get('file')
            language = form.cleaned_data.get('language', 'en')
            voice = form.cleaned_data.get('voice', 'en-US-AriaNeural')
            speed = form.cleaned_data.get('speed', 'normal')
            title = form.cleaned_data.get('title')

            # Extract text from file if provided
            if uploaded_file:
                try:
                    ext = uploaded_file.name.split('.')[-1].lower()
                    if ext == 'txt':
                        text = uploaded_file.read().decode('utf-8', errors='ignore')
                    elif ext == 'pdf':
                        # Use PyPDF2 PdfReader to extract text
                        pdf_file = io.BytesIO(uploaded_file.read())
                        reader = PdfReader(pdf_file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() or ""
                except Exception as e:
                    messages.error(request, f"Failed to parse file: {str(e)}")
                    return render(request, 'converter/convert.html', {'form': form})

            text = text.strip()
            if not text:
                messages.error(request, "Please enter some text or upload a valid file.")
                return render(request, 'converter/convert.html', {'form': form})

            # Word count calculation
            word_count = len(text.split())

            try:
                # Text to Speech using edge-tts (asynchronous)
                from asgiref.sync import async_to_sync
                import edge_tts
                
                rate = "-25%" if speed == 'slow' else "+0%"
                
                async def generate_edge_tts_audio(text_content, voice_name, speech_rate):
                    communicate = edge_tts.Communicate(text_content, voice_name, rate=speech_rate)
                    audio_io = io.BytesIO()
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_io.write(chunk["data"])
                    audio_io.seek(0)
                    return audio_io

                # Run the async synthesis inside synchronous view
                audio_io = async_to_sync(generate_edge_tts_audio)(text, voice, rate)

                # Create Model instance
                conversion = form.save(commit=False)
                conversion.user = request.user if request.user.is_authenticated else None
                conversion.original_text = text
                conversion.word_count = word_count
                
                if not title:
                    # Generate title from first few words
                    words = text.split()[:4]
                    conversion.title = " ".join(words)[:50] or f"Conversion - {datetime.date.today().strftime('%Y-%m-%d')}"
                
                # Generate clean safe filename
                safe_title = "".join([c if c.isalnum() else "_" for c in conversion.title[:20]])
                filename = f"{safe_title}_{voice}.mp3"
                
                # Save audio file to model field
                conversion.audio_file.save(filename, ContentFile(audio_io.read()), save=False)
                conversion.save()

                if request.user.is_authenticated:
                    messages.success(request, f"Successfully converted! Saved as '{conversion.title}'.")
                    return redirect('dashboard')
                else:
                    # For guest users, pass the file object directly for immediate playback/download
                    messages.success(request, "Conversion successful! Download your audio below.")
                    return render(request, 'converter/convert.html', {
                        'form': form,
                        'guest_audio': conversion.audio_file.url,
                        'guest_title': conversion.title,
                        'word_count': word_count
                    })

            except Exception as e:
                messages.error(request, f"An error occurred during speech synthesis: {str(e)}")
                return render(request, 'converter/convert.html', {'form': form})
    else:
        form = AudioConversionForm()

    return render(request, 'converter/convert.html', {'form': form})

@login_required
def dashboard_view(request):
    """User dashboard view showing conversion list, search, and statistics."""
    query = request.GET.get('q', '').strip()
    conversions = AudioConversion.objects.filter(user=request.user)

    if query:
        conversions = conversions.filter(
            Q(title__icontains=query) | Q(original_text__icontains=query)
        )

    conversions = conversions.order_by('-created_at')

    # Calculate statistics
    stats = conversions.aggregate(
        total_words=Sum('word_count'),
    )
    total_conversions = conversions.count()
    total_words = stats.get('total_words') or 0

    # Get most used language
    lang_counts = {}
    for c in conversions:
        lang_counts[c.language] = lang_counts.get(c.language, 0) + 1
    most_used_lang = max(lang_counts, key=lang_counts.get).upper() if lang_counts else 'N/A'

    context = {
        'conversions': conversions,
        'query': query,
        'total_conversions': total_conversions,
        'total_words': total_words,
        'most_used_lang': most_used_lang,
    }
    return render(request, 'converter/dashboard.html', context)

@login_required
def delete_conversion(request, pk):
    """Delete a conversion record and its associated audio file."""
    conversion = get_object_or_404(AudioConversion, pk=pk, user=request.user)
    if request.method == 'POST':
        title = conversion.title
        conversion.delete()
        
        # If AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': f"Deleted '{title}'"})
            
        messages.success(request, f"Deleted conversion '{title}'")
        return redirect('dashboard')
        
    return redirect('dashboard')

def signup_view(request):
    """User signup view with direct login after success."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome to Text-to-Audio Pro.")
            return redirect('dashboard')
    else:
        form = UserCreationForm()
        
    return render(request, 'registration/signup.html', {'form': form})
