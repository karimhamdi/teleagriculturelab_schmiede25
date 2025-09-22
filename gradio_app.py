import gradio as gr
import requests  # Or the library for "nanobanana"
import os
from PIL import Image
import io

# --- Hypothetical settings for the nanobanana Gemini API ---
# You would get these from the API's documentation
API_KEY = os.environ.get("GEMINI_API_KEY") # It's best to use environment variables for keys
API_ENDPOINT = "https://api.gemini-nanobanana.com/v1/images/generate"

# Global variable to store the image path
current_image = None

def get_daily_image():
    """
    This function generates a new image using the hypothetical Gemini/nanobanana API.
    """
    global current_image

    # If no API key is configured, use a placeholder image URL
    if not API_KEY:
        placeholder_url = "https://picsum.photos/1024/1024"
        try:
            resp = requests.get(placeholder_url, timeout=30)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            current_image = img
            return img
        except requests.exceptions.RequestException as e:
            print(f"Error fetching placeholder image: {e}")
            # Minimal fallback: gray image
            img = Image.new("RGB", (1024, 1024), color=(200, 200, 200))
            current_image = img
            return img

    # --- This is the part you would adapt for the actual API ---
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": "A beautiful, artistic image for my daily display",
        "size": "1024x1024",
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        image_url = response.json().get("imageUrl")
        if not image_url:
            # Fallback if API didn't return what we expected
            image_url = "https://picsum.photos/1024/1024?blur=1"
        # Fetch the image content and return a PIL image
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
        current_image = img
        print(f"Updated image from: {image_url}")
        return img
    except requests.exceptions.RequestException as e:
        print(f"Error calling the image API: {e}")
        # Fallback to a basic grayscale image
        img = Image.new("RGB", (1024, 1024), color=(128, 128, 128))
        current_image = img
        return img

def create_app():
    """Creates and returns the Gradio app."""
    with gr.Blocks(title="Daily Image") as app:
        gr.Markdown("# Your Daily Image")
        image_output = gr.Image(value=None, label="Today's Image")

        # Run once at load to populate the image
        app.load(get_daily_image, None, image_output)

        # Add a manual refresh button
        refresh_btn = gr.Button("Refresh now")
        refresh_btn.click(get_daily_image, None, image_output)

        # Use a Gradio Timer to update the image periodically (24 hours)
        # Note: This triggers relative to when the app starts
        timer = gr.Timer(86400, active=True)
        timer.tick(get_daily_image, None, image_output)
    return app

if __name__ == "__main__":
    # Create and launch the Gradio app
    app = create_app()
    app.launch()