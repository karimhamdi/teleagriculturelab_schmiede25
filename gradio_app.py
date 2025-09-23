from typing import Tuple
from PIL import Image, ImageDraw, ImageFont


WEATHER_PNG_PATH = None  # disk fallback removed
GENERATED_PNG_PATH = None  # disk fallback removed

def _placeholder_image(size: Tuple[int, int], text: str, bg=(230, 230, 230)) -> Image.Image:
    # Always create a simple placeholder; don't try to read a file here
    img = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text(((size[0] - w) / 2, (size[1] - h) / 2), text, fill=(80, 80, 80), font=font)
    return img


def load_weather_plot(size: Tuple[int, int] = (1024, 1024)) -> Image.Image:
    """Load the weather plot image produced by weather_data_visualisation.py.

    Attempts to import the script to generate the file on first run. Falls back
    to a placeholder if unavailable.
    """
    try:
        # Prefer calling the function to get a PIL image directly
        from weather_data_visualisation import weather_data_visualisation

        img = weather_data_visualisation(save_to_disk=False)
        if isinstance(img, Image.Image):
            if img.size != size:
                img = img.resize(size, Image.LANCZOS)
            return img
    except Exception as e:
        print(f"Weather plot generation failed: {e}")

    return _placeholder_image(size, "Weather plot unavailable")


def load_genai_output(size: Tuple[int, int] = (1024, 1024)) -> Image.Image:
    """Load the GenAI output image if available; otherwise return a placeholder.

    If `genai.py` later exposes a function like `generate_genai_image(size)`,
    it will be used here automatically.
    """
    try:
        from genai import generate_genai_image

        # Provide the latest weather image if possible to guide the GenAI
        base_img = None
        try:
            base_img = load_weather_plot(size)
        except Exception:
            base_img = None

        img = generate_genai_image(input_image=base_img, save_to_disk=False)
        if isinstance(img, Image.Image):
            if img.size != size:
                img = img.resize(size, Image.LANCZOS)
            return img
    except Exception as e:
        print(f"genai.py not usable yet: {e}")

    return _placeholder_image(size, "GenAI image pending")


def get_both_images(size: Tuple[int, int] = (1024, 1024)) -> Tuple[Image.Image, Image.Image]:
    left = load_weather_plot(size)
    right = load_genai_output(size)
    return left, right


def create_app():
    """Creates and returns the Gradio app with two side-by-side images."""
    import gradio as gr

    with gr.Blocks(title="Weather × GenAI") as app:
        gr.Markdown("# Weather visualization and GenAI output")
        with gr.Row():
            left_img = gr.Image(label="Weather plot", type="pil")
            right_img = gr.Image(label="GenAI output", type="pil")

        # Load both images on app start
        app.load(fn=get_both_images, inputs=None, outputs=[left_img, right_img])

        # Manual refresh button
        refresh_btn = gr.Button("Refresh")
        refresh_btn.click(fn=get_both_images, inputs=None, outputs=[left_img, right_img])

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch()