from flask import Flask, render_template, request, send_from_directory
from PyPDF2 import PdfFileReader
from gtts import gTTS
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'static/audio'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    text = request.form.get('text', '')

    # Check if the text input is provided and limit it to 1000 words
    if text:
        word_count = len(text.split())
        if word_count > 1000:
            return 'Text exceeds 1000 words limit', 400

    # If a file is uploaded, process the file
    if file and file.filename.endswith(('.pdf', '.txt')):
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        if file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif file.filename.endswith('.txt'):
            text = file.read().decode('utf-8')

    # Convert the text to audio if text is available
    if text:
        audio_file = convert_text_to_audio(text)
        return send_from_directory(AUDIO_FOLDER, audio_file, as_attachment=True)

    return 'Invalid input: either upload a file or enter text within the 1000 words limit', 400

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PdfFileReader(file)
        text = ''
        for page_num in range(reader.getNumPages()):
            page = reader.getPage(page_num)
            text += page.extract_text()
    return text

def convert_text_to_audio(text):
    tts = gTTS(text)
    audio_file = 'output.mp3'
    audio_path = os.path.join(AUDIO_FOLDER, audio_file)
    tts.save(audio_path)
    return audio_file

if __name__ == '__main__':
    app.run(debug=True)
