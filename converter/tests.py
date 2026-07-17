from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import AudioConversion
from .forms import AudioConversionForm

class AudioConversionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_model_creation(self):
        conversion = AudioConversion.objects.create(
            user=self.user,
            title='Test Audio',
            original_text='This is a simple test sentence.',
            language='en',
            voice='en-US-AriaNeural',
            speed='normal',
            word_count=6
        )
        self.assertEqual(conversion.title, 'Test Audio')
        self.assertEqual(conversion.user.username, 'testuser')
        self.assertEqual(str(conversion), 'Test Audio (en-US-AriaNeural)')

class AudioConversionFormTest(TestCase):
    def test_empty_form_invalid(self):
        # Empty title, text, and file should fail
        form = AudioConversionForm(data={'title': '', 'language': 'en', 'voice': 'en-US-AriaNeural', 'speed': 'normal'})
        self.assertFalse(form.is_valid())

    def test_text_provided_valid(self):
        form = AudioConversionForm(data={
            'title': 'My Title',
            'text': 'A quick brown fox jumps over the lazy dog',
            'language': 'en',
            'voice': 'en-US-AriaNeural',
            'speed': 'normal'
        })
        self.assertTrue(form.is_valid())

    def test_word_limit_validation(self):
        # Create a string of 1001 words, should be valid now that limits are removed
        long_text = "word " * 1001
        form = AudioConversionForm(data={
            'title': 'Long Audio',
            'text': long_text,
            'language': 'en',
            'voice': 'en-US-AriaNeural',
            'speed': 'normal'
        })
        self.assertTrue(form.is_valid())

class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_convert_page_loads(self):
        response = self.client.get(reverse('convert'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transform Text to Speech')

    def test_signup_page_loads(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')

    def test_dashboard_redirects_for_anonymous(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302) # Redirects to login

