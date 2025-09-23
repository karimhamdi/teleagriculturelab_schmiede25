from dotenv import load_dotenv
from PIL import Image
from typing import Optional
from io import BytesIO

load_dotenv()  # take environment variables from .env.

from google import genai

client = genai.Client()

# Default creative prompt
DEFAULT_PROMPT = (
    "Turn the provided data visualization into a painting using an eastern art style."
)


def generate_genai_image(
    input_image: Optional[Image.Image] = None,
    prompt: Optional[str] = None,
    model: str = "gemini-2.5-flash-image-preview",
    save_to_disk: bool = False,
) -> Optional[Image.Image]:
    """Generate a stylized image from an input PIL image using Google GenAI.

    Args:
        input_image: Source PIL image. If None, calls weather_data_visualisation() to generate in-memory.
        prompt: Optional text prompt; falls back to DEFAULT_PROMPT.
        model: Model name to use.
        save_to_disk: When True, saves to output/generated_image.png (no disk reads occur).

    Returns:
        A PIL.Image on success, or None if generation failed.
    """

    # Resolve input image strictly in-memory
    img = input_image
    if img is None:
        try:
            from weather_data_visualisation import weather_data_visualisation

            img = weather_data_visualisation(save_to_disk=False)
        except Exception:
            img = None

    if img is None:
        return None

    # Prepare prompt
    ptxt = prompt or DEFAULT_PROMPT

    try:
        response = client.models.generate_content(
            model=model,
            contents=[ptxt, img],
        )
    except Exception as e:
        # No credentials or API issue
        print(f"GenAI request failed: {e}")
        return None

    output_image = None
    try:
        for part in response.candidates[0].content.parts:
            if getattr(part, "text", None) is not None:
                # Optional: print any textual response
                print(part.text)
            elif getattr(part, "inline_data", None) is not None:
                output_image = Image.open(BytesIO(part.inline_data.data)).convert("RGB")
    except Exception as e:
        print(f"Failed to parse GenAI response: {e}")
        return None

    # Optional save without using as a future fallback
    if output_image is not None and save_to_disk:
        try:
            import os

            os.makedirs("output", exist_ok=True)
            output_image.save("output/generated_image.png")
        except Exception:
            pass

    return output_image

if __name__ == "__main__":
    generate_genai_image()