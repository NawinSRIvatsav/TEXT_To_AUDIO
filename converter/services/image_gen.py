import os
import torch
from diffusers import StableDiffusionPipeline, StableDiffusionImg2ImgPipeline
from PIL import Image
import io

_txt2img_pipe = None
_img2img_pipe = None
MODEL_ID = "stabilityai/sd-turbo"  # Extremely fast, 1 step, high quality!

STYLE_PRESETS = {
    'realistic': "photorealistic, highly detailed, 8k resolution, cinematic lighting, photoreal, masterpiece",
    'anime': "anime style, digital illustration, vibrant colors, detailed line art, studio ghibli aesthetic",
    'watercolor': "watercolor painting, soft washes, textured paper, artistic brush strokes, beautiful masterpiece",
    'pixel': "16-bit retro pixel art, video game style, colorful block colors, detailed textures"
}

def get_device():
    """Detects available computing device (CUDA or CPU)."""
    return "cuda" if torch.cuda.is_available() else "cpu"

def get_txt2img_pipeline():
    """Initializes and returns cached Text-to-Image Stable Diffusion pipeline."""
    global _txt2img_pipe
    if _txt2img_pipe is None:
        device = get_device()
        dtype = torch.float16 if device == "cuda" else torch.float32
        
        # Load pipeline locally (auto-downloads weights on first run)
        _txt2img_pipe = StableDiffusionPipeline.from_pretrained(
            MODEL_ID, 
            torch_dtype=dtype
        )
        
        if device == "cuda":
            _txt2img_pipe.to("cuda")
            # Enable memory efficient attention to save VRAM
            try:
                _txt2img_pipe.enable_attention_slicing()
                _txt2img_pipe.enable_xformers_memory_efficient_attention()
            except Exception:
                pass
        else:
            _txt2img_pipe.to("cpu")
            
    return _txt2img_pipe

def get_img2img_pipeline():
    """Initializes and returns cached Image-to-Image pipeline sharing components with txt2img."""
    global _img2img_pipe
    if _img2img_pipe is None:
        device = get_device()
        dtype = torch.float16 if device == "cuda" else torch.float32
        
        # Load and share components to avoid duplicate memory consumption
        txt2img = get_txt2img_pipeline()
        _img2img_pipe = StableDiffusionImg2ImgPipeline(
            vae=txt2img.vae,
            text_encoder=txt2img.text_encoder,
            tokenizer=txt2img.tokenizer,
            unet=txt2img.unet,
            scheduler=txt2img.scheduler,
            safety_checker=txt2img.safety_checker,
            feature_extractor=txt2img.feature_extractor,
            requires_safety_checker=True
        )
        if device == "cuda":
            _img2img_pipe.to("cuda")
            try:
                _img2img_pipe.enable_attention_slicing()
            except Exception:
                pass
        else:
            _img2img_pipe.to("cpu")
            
    return _img2img_pipe

def run_txt2img(prompt, style_preset="realistic") -> Image.Image:
    """Generates an image from a prompt and style preset locally."""
    pipe = get_txt2img_pipeline()
    
    # Apply style preset modifiers to prompt
    preset_modifier = STYLE_PRESETS.get(style_preset, "")
    full_prompt = f"{prompt}, {preset_modifier}"
    
    # Run inference (sd-turbo works beautifully in 1-4 steps!)
    # num_inference_steps=1 is standard for sd-turbo. Let's use 2 steps for extra detail.
    image = pipe(
        prompt=full_prompt, 
        num_inference_steps=2, 
        guidance_scale=0.0
    ).images[0]
    
    return image

def run_img2img(prompt, init_image_bytes, strength=0.7, style_preset="anime") -> Image.Image:
    """Stylizes an uploaded image using image-to-image stable diffusion locally."""
    pipe = get_img2img_pipeline()
    
    # Convert bytes to PIL Image
    init_image = Image.open(io.BytesIO(init_image_bytes)).convert("RGB")
    init_image = init_image.resize((512, 512)) # Standard SD input sizing
    
    preset_modifier = STYLE_PRESETS.get(style_preset, "")
    full_prompt = f"{prompt}, {preset_modifier}"
    
    # Run image-to-image inference
    image = pipe(
        prompt=full_prompt,
        image=init_image,
        strength=strength,
        num_inference_steps=4,
        guidance_scale=1.0
    ).images[0]
    
    return image


_inpaint_pipe = None

def get_inpaint_pipeline():
    """Initializes and returns cached Inpainting pipeline sharing components with txt2img."""
    global _inpaint_pipe
    if _inpaint_pipe is None:
        device = get_device()
        dtype = torch.float16 if device == "cuda" else torch.float32
        
        # Load and share components
        txt2img = get_txt2img_pipeline()
        from diffusers import StableDiffusionInpaintPipeline
        _inpaint_pipe = StableDiffusionInpaintPipeline(
            vae=txt2img.vae,
            text_encoder=txt2img.text_encoder,
            tokenizer=txt2img.tokenizer,
            unet=txt2img.unet,
            scheduler=txt2img.scheduler,
            safety_checker=txt2img.safety_checker,
            feature_extractor=txt2img.feature_extractor,
            requires_safety_checker=True
        )
        if device == "cuda":
            _inpaint_pipe.to("cuda")
        else:
            _inpaint_pipe.to("cpu")
            
    return _inpaint_pipe

def run_inpaint(prompt, init_image_bytes, mask_image_bytes, style_preset="realistic") -> Image.Image:
    """Edits details in an image based on a prompt and black-and-white mask locally."""
    pipe = get_inpaint_pipeline()
    
    init_image = Image.open(io.BytesIO(init_image_bytes)).convert("RGB").resize((512, 512))
    mask_image = Image.open(io.BytesIO(mask_image_bytes)).convert("L").resize((512, 512)) # Mask must be grayscale (L)
    
    preset_modifier = STYLE_PRESETS.get(style_preset, "")
    full_prompt = f"{prompt}, {preset_modifier}"
    
    # Run inpainting inference
    image = pipe(
        prompt=full_prompt,
        image=init_image,
        mask_image=mask_image,
        num_inference_steps=4,
        guidance_scale=1.5
    ).images[0]
    
    return image
