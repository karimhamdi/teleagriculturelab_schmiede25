from dotenv import load_dotenv
from PIL import Image
import os
load_dotenv()  # take environment variables from .env.

from google import genai
from PIL import Image
from io import BytesIO

client = genai.Client()

#prompt = ("Using the provided data visualization, please add photorealistic Chinese tea snacks to the scene. Ensure the change is supports the visualization.")
prompt = ("Turn the provided data visualization into a painting using an eastern art style.")

def generate_genai_image():
    
    image = Image.open("output/monsoon_mandala_example.png").convert("RGB")

    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=[prompt, image],
    )

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save("output/generated_image.png")

if __name__ == "__main__":
    generate_genai_image()