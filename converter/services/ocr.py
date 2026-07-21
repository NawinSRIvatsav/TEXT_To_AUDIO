import cv2
import numpy as np
import easyocr

_reader = None

def get_easyocr_reader():
    """Initializes and returns cached EasyOCR reader to avoid reloading weights."""
    global _reader
    if _reader is None:
        # Load reader for English (easyocr will download models on first run locally)
        _reader = easyocr.Reader(['en'], gpu=False) # Keep gpu=False for cpu default stability, PyTorch will auto-detect CUDA if config allows
    return _reader

def preprocess_image(image_bytes):
    """Preprocesses image bytes using OpenCV for better OCR accuracy."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes.")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=3)
    
    # Adaptive thresholding (binarization)
    thresholded = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    return thresholded

def extract_text_from_image(image_bytes) -> str:
    """Extracts text from uploaded image bytes locally."""
    reader = get_easyocr_reader()
    try:
        processed = preprocess_image(image_bytes)
        results = reader.readtext(processed)
        if not results:
            # Fallback to direct raw image if thresholding was too aggressive
            nparr = np.frombuffer(image_bytes, np.uint8)
            raw_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            results = reader.readtext(raw_img)
    except Exception:
        # Fallback to direct raw image
        nparr = np.frombuffer(image_bytes, np.uint8)
        raw_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if raw_img is None:
            return ""
        results = reader.readtext(raw_img)

    text_list = [res[1] for res in results]
    return " ".join(text_list).strip()

def extract_text_from_frame(frame: np.ndarray) -> list[dict]:
    """
    Extracts text and coordinates from a webcam frame.
    Returns a list of dicts: [{'text': str, 'confidence': float, 'box': [[x,y],...]}]
    """
    reader = get_easyocr_reader()
    results = reader.readtext(frame)
    
    ocr_results = []
    for bbox, text, conf in results:
        # Convert numpy coordinates to standard python types for JSON serialization
        coords = [[int(pt[0]), int(pt[1])] for pt in bbox]
        ocr_results.append({
            'text': text,
            'confidence': float(conf),
            'box': coords
        })
    return ocr_results
