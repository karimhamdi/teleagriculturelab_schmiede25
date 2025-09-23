from dotenv import load_dotenv
from PIL import Image
from typing import Optional
from io import BytesIO
import time

load_dotenv()  # take environment variables from .env.

from google import genai

client = genai.Client()

# Default creative prompt


description = """This project uses publicly engaged artistic approaches to raise awareness of food and the environment, using a de-anthropocentric and objective approach to remediate historical narratologies and engagements for contemporary audiences.  Using microbial orientated foods as an interface to communicate scientific, cultural and political investigations into local ecologies through art, this project presents itself as a riverbank buffet of fermented foods, beverages and ideas, all intersecting through a singular themed event, along the shores of the Tamsui River. Presented as a dégustation menu, each course will consist of an edible dish, paired with a drink and an ecological artwork, taking the audience on a journey from underground, through soil and water to the sky and back with the aim of allowing participants to more clearly see the historical, present and future ecologies of chosen location for this event. 

Inspired by the Umberto Eco novel The Island of the Day Before is a project Stadon started in 2022 with the aim to explore what we can learn through revisiting historical approaches and engagement with ecology; be they Art’s overly romanticised engagement with nature and the sublime, historical artistic engagements with agriculture, food and ecology, through to more recent fetishizations of food in social media. This is also integrated with scientific research and adopts both qualitative and quantitative approaches communicating food ecologies through art and how its modes of representation and reflection have changed since Industrialisation, Urbanisation, Digitisation, Networking and Bio-Technologies, up until what we now can define as the Post-Anthropocentric Era.

Consisting of a dinner with performative, post-natural and bio-digital artworks along with a formal artist talk and an informal, conversational workshop, this event aims to ferment new perspectives on food systems, ecology, culture and society, through participation in  micro-macro sub-connectivities and entanglements in ecological systems, post-natural ideologies, microbial and fungal remedies and molecular transitions in human and non-human bodily encounters. 

This residency acted as both a research and development residency and an opportunity to try a recently developed curatorial approach of integrating, artworks, scientific findings, storytelling and performance into a multi-course themed dinner, using exclusively locally sourced foods.
"""

def pick_artstyle(description=description, model: str = "gemini-2.5-flash-image-preview") -> str:
    client = genai.Client()
    prompt = f""" '{description}'
    read this project description, and choose an artistic style to represent it with.
    Respond only with two words.

    Example output:
    Abstract Expressionism

    Cubist Geometry

    Surreal Dreamscape

    Minimal Maximalism

    Neo Baroque

    High Renaissance

    Northern Renaissance

    Pop Surrealism

    Conceptual Minimalism

    Color Field

    Geometric Abstraction

    Figurative Expressionism

    Lyrical Abstraction

    Social Realism

    Magical Realism

    Socialist Realism

    Hyper Realism

    Post Impressionism

    Neo Impressionism

    Abstract Minimalism

    Digital Collage

    Generative Aesthetics

    Vaporwave Aesthetics

    Glitch Aesthetics

    Kinetic Sculpture

    Optical Abstraction

    Constructivist Graphics

    Bauhaus Modernism

    International Style"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt],
        )
    except Exception as e:
        # No credentials or API issue
        print(f"GenAI request failed: {e}")
        return None
    
    try:
        for part in response.candidates[0].content.parts:
            if getattr(part, "text", None) is not None:
                # Optional: print any textual response
                art_style = part.text
            elif getattr(part, "inline_data", None) is not None:
                output_image = Image.open(BytesIO(part.inline_data.data)).convert("RGB")
    except Exception as e:
        print(f"pick_artstyle: Failed to parse GenAI response: {e}")
        return prompt

    return art_style

art_style = "eastern"

def gen_default_prompt(art_style = art_style) -> str:
    return (
        f"Turn the provided data visualization into a painting using an {art_style} art style."
    )

DEFAULT_PROMPT = gen_default_prompt()

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
        print("No input image available for GenAI.")
        return None

    # Prepare prompt
    ptxt = prompt or DEFAULT_PROMPT

    output_image = None
    last_error = None

    # Retry up to 5 times, waiting 2 seconds between failed attempts
    for attempt in range(1, 6):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[ptxt, img],
            )
        except Exception as e:
            last_error = e
            # If not last attempt, wait and retry
            if attempt < 5:
                time.sleep(2)
                continue
            else:
                print(f"GenAI request failed (attempt {attempt}/5): {e}")
                break

        try:
            # Reset on each attempt
            output_image = None
            for part in response.candidates[0].content.parts:
                if getattr(part, "text", None) is not None:
                    # Optional: print any textual response
                    print(part.text)
                elif getattr(part, "inline_data", None) is not None:
                    output_image = Image.open(BytesIO(part.inline_data.data)).convert("RGB")
            # Success condition
            if output_image is not None:
                break
        except Exception as e:
            last_error = e
            # Parsing failed; if not last attempt, wait and retry
            if attempt < 5:
                time.sleep(2)
                continue
            else:
                print(f"Failed to parse GenAI response (attempt {attempt}/5): {e}")
                break

        # If we reached here with no image, wait then try again (unless last attempt)
        if output_image is None and attempt < 5:
            time.sleep(2)

    # Optional save without using as a future fallback
    if output_image is not None and save_to_disk:
        try:
            import os

            os.makedirs("output", exist_ok=True)
            output_image.save("output/generated_image.png")
        except Exception:
            pass

    if output_image is None and last_error is not None:
        # Keep return type unchanged; logging already printed above
        pass

    return output_image

if __name__ == "__main__":
    DEFAULT_PROMPT = gen_default_prompt(pick_artstyle())
    print(DEFAULT_PROMPT)
    img = Image.open("output/monsoon_mandala_example.png")
    generate_genai_image(input_image=img, save_to_disk=True)
