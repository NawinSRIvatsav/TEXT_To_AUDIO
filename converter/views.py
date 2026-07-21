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
            generate_video = form.cleaned_data.get('generate_video', False)
            video_style = form.cleaned_data.get('video_style', 'waveform')

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

            # Feature 1: Translation processing
            translate_before_converting = form.cleaned_data.get('translate_before_converting', False)
            target_language = form.cleaned_data.get('target_language', 'en')
            was_translated = False
            original_text_backup = text
            source_language = 'auto'

            if translate_before_converting and target_language:
                try:
                    translated, detected_lang = translate_text(text, 'auto', target_language)
                    source_language = detected_lang
                    text = translated
                    was_translated = True
                    language = target_language
                    
                    # Fallback voice selection if currently selected voice doesn't match target language
                    if not voice.startswith(target_language):
                        from .forms import VOICE_MAP
                        voices_list = VOICE_MAP.get(target_language, [])
                        if voices_list:
                            voice = voices_list[0][0]
                except TranslationError as e:
                    messages.error(request, f"Translation failed: {str(e)}")
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
                conversion.original_text = original_text_backup
                conversion.word_count = word_count
                
                # Assign translation fields
                conversion.source_language = source_language
                conversion.translated_text = text if was_translated else None
                conversion.was_translated = was_translated
                conversion.language = language
                conversion.voice = voice
                
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

                if generate_video:
                    conversion.video_style = video_style
                    conversion.save()
                    if request.user.is_authenticated:
                        from django_q.tasks import async_task
                        async_task('converter.tasks.generate_video_task', conversion.id)

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

from django.views.decorators.csrf import csrf_exempt
from .services.translation import translate_text, TranslationError

@csrf_exempt
def translate_preview(request):
    """AJAX preview endpoint that returns translated text and detected source language."""
    if request.method == 'POST':
        text = request.POST.get('text', '')
        target_lang = request.POST.get('target_lang', 'en')
        source_lang = request.POST.get('source_lang', 'auto')

        if not text:
            return JsonResponse({'status': 'error', 'message': 'No text provided'}, status=400)

        try:
            translated, detected_lang = translate_text(text, source_lang, target_lang)
            return JsonResponse({
                'status': 'success',
                'translated_text': translated,
                'detected_lang': detected_lang
            })
        except TranslationError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

from .services.ocr import extract_text_from_image, extract_text_from_frame
import numpy as np
import cv2

@csrf_exempt
def ocr_upload(request):
    """AJAX endpoint to perform OCR on an uploaded image file."""
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'status': 'error', 'message': 'No image file uploaded.'}, status=400)
        
        try:
            image_bytes = image_file.read()
            extracted_text = extract_text_from_image(image_bytes)
            if not extracted_text:
                return JsonResponse({'status': 'error', 'message': 'No text could be detected in this image. Try a sharper, high-contrast image.'})
            return JsonResponse({'status': 'success', 'text': extracted_text})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"OCR failure: {str(e)}"}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

@csrf_exempt
def ocr_frame(request):
    """AJAX endpoint to perform real-time OCR on a webcam JPEG blob frame."""
    if request.method == 'POST':
        frame_file = request.FILES.get('frame')
        if not frame_file:
            return JsonResponse({'status': 'error', 'message': 'No frame received.'}, status=400)
            
        try:
            frame_bytes = frame_file.read()
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return JsonResponse({'status': 'error', 'message': 'Invalid frame data.'}, status=400)
                
            results = extract_text_from_frame(img)
            return JsonResponse({'status': 'success', 'results': results})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Frame OCR failure: {str(e)}"}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

def scan_webcam_view(request):
    """Render the real-time webcam scanning portal."""
    return render(request, 'converter/scan.html')

@login_required
def image_generator_view(request):
    """View to handle text-to-image, img2img, and inpainting generation tasks."""
    if request.method == 'POST':
        mode = request.POST.get('mode', 'txt2img')  # txt2img, img2img, inpaint
        prompt = request.POST.get('prompt', '').strip()
        style = request.POST.get('style', 'realistic')

        if not prompt:
            messages.error(request, "Please enter a description prompt.")
            return redirect('image_generator')

        from django_q.tasks import async_task

        if mode == 'txt2img':
            async_task('converter.tasks.generate_image_task', request.user.id, prompt, style)
            messages.success(request, "Text-to-Image request submitted! Your image is being generated in the background locally.")
        
        elif mode == 'img2img':
            image_file = request.FILES.get('image')
            strength = float(request.POST.get('strength', 0.7))
            if not image_file:
                messages.error(request, "Please upload an initial image to stylize.")
                return redirect('image_generator')
            
            image_bytes = image_file.read()
            async_task('converter.tasks.generate_img2img_task', request.user.id, prompt, image_bytes, strength, style)
            messages.success(request, "Image Stylization request submitted! Processing initial image locally in background.")
            
        elif mode == 'inpaint':
            image_file = request.FILES.get('image')
            mask_file = request.FILES.get('mask_image')
            if not image_file or not mask_file:
                messages.error(request, "Please provide both the source image and drawn mask.")
                return redirect('image_generator')
            
            image_bytes = image_file.read()
            mask_bytes = mask_file.read()
            async_task('converter.tasks.generate_inpaint_task', request.user.id, prompt, image_bytes, mask_bytes, style)
            messages.success(request, "Inpainting task submitted! Editing image details in the background locally.")

        return redirect('image_generator')

    # GET request: load user's generated images
    images = GeneratedImage.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'converter/image_gen.html', {'images': images})

@login_required
def delete_image(request, pk):
    """Deletes a generated image and cleans up its file from disk."""
    image = get_object_or_404(GeneratedImage, pk=pk, user=request.user)
    if request.method == 'POST':
        prompt_snippet = image.prompt[:20]
        image.delete()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': f"Deleted image '{prompt_snippet}'"})
            
        messages.success(request, f"Deleted image '{prompt_snippet}'")
    return redirect('image_generator')
