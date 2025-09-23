from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import pandas as pd


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


def load_weather_plot(
    size: Tuple[int, int] = (1024, 1024),
    kit_id: Optional[int] = None,
    df: Optional[pd.DataFrame] = None,
) -> Image.Image:
    """Load the weather plot image for a given kit.

    Tries to generate in-memory via weather_data_visualisation(); falls back to
    a placeholder if unavailable.
    """
    try:
        # Prefer calling the function to get a PIL image directly
        from weather_data_visualisation import weather_data_visualisation

        img = weather_data_visualisation(kit=kit_id, df=df, save_to_disk=False)
        if isinstance(img, Image.Image):
            if img.size != size:
                img = img.resize(size, Image.LANCZOS)
            return img
    except Exception as e:
        print(f"Weather plot generation failed: {e}")

    return _placeholder_image(size, "Weather plot unavailable")


def load_genai_output(
    size: Tuple[int, int] = (1024, 1024),
    kit_id: Optional[int] = None,
    df: Optional[pd.DataFrame] = None,
) -> Image.Image:
    """Load the GenAI output image for a given kit if available; otherwise a placeholder.

    Uses the selected kit's weather plot as the guiding input for the GenAI image.
    """
    try:
        from genai import generate_genai_image

        # Provide the latest weather image if possible to guide the GenAI
        base_img = None
        try:
            base_img = load_weather_plot(size, kit_id=kit_id, df=df)
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


def get_both_images(
    kit_id: Optional[int] = None,
    df: Optional[pd.DataFrame] = None,
    size: Tuple[int, int] = (1024, 1024),
) -> Tuple[Image.Image, Image.Image]:
    left = load_weather_plot(size, kit_id=kit_id, df=df)
    right = load_genai_output(size, kit_id=kit_id, df=df)
    return left, right


def create_app():
    """Creates and returns the Gradio app with two side-by-side images."""
    import gradio as gr
    import pandas as pd

    with gr.Blocks(title="Weather × GenAI") as app:
        gr.Markdown("# Weather visualization and GenAI output")
        
        # State to hold the loaded DataFrame
        df_state = gr.State()

        with gr.Row():
            kit_input = gr.Number(label="Kit ID", value=1001, precision=0)
        with gr.Row():
            left_img = gr.Image(label="Weather plot", type="pil")
            right_img = gr.Image(label="GenAI output", type="pil")
        status_md = gr.Markdown(visible=True)

        # Helper functions inside the app context to use gr.update
        def _disable_refresh():
            # Immediately disable the refresh button before a long-running task
            return gr.update(interactive=False)

        def _prepare_data(kit_id):
            # Fetch data for the given kit to ensure availability before enabling generation
            try:
                from utils import get_kit_measurements_df

                kit = 1001
                if kit_id is not None:
                    try:
                        kit = int(kit_id)
                    except Exception:
                        kit = 1001

                df = get_kit_measurements_df(kit)
                if df is None or getattr(df, "empty", True):
                    return (
                        f"No data found for kit {kit}. Please try another kit.",
                        gr.update(interactive=False),
                        None,
                    )
                return (
                    f"Data loaded for kit {kit}: {len(df)} rows.",
                    gr.update(interactive=True),
                    df,
                )
            except Exception as e:
                return (f"Failed to load data: {e}", gr.update(interactive=False), None)

        # Manual refresh button
        refresh_btn = gr.Button("Refresh")
        refresh_btn.click(
            fn=get_both_images,
            inputs=[kit_input, df_state],
            outputs=[left_img, right_img],
        )

        # On app load: disable -> prepare data -> then render initial images
        (
            app.load(fn=_disable_refresh, inputs=None, outputs=refresh_btn)
            .then(
                fn=_prepare_data,
                inputs=[kit_input],
                outputs=[status_md, refresh_btn, df_state],
            )
            .then(
                fn=get_both_images,
                inputs=[kit_input, df_state],
                outputs=[left_img, right_img],
            )
        )

        # When kit changes: disable button immediately, then prepare data; user can then click Refresh
        (
            kit_input.change(fn=_disable_refresh, inputs=None, outputs=refresh_btn)
            .then(
                fn=_prepare_data,
                inputs=[kit_input],
                outputs=[status_md, refresh_btn, df_state],
            )
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch()