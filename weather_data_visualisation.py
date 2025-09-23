# This script generates a sample "Monsoon Mandala" artwork using placeholder data. 
# Replace the synthetic data block with your real pandas DataFrame columns to recreate the piece with your tea farm data.

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from PIL import Image
from typing import Optional
from utils import get_kit_measurements_df


def weather_data_visualisation(
    kit: int = 1001,
    save_to_disk: bool = False,
    df: Optional[pd.DataFrame] = None,
) -> Image.Image:
    """Generates a 'Monsoon Mandala' visualization from weather data.

    Args:
        kit: The kit ID to fetch data for, if df is not provided.
        save_to_disk: Whether to save the output image to disk.
        df: An optional DataFrame with pre-loaded weather data. If None, data will be fetched.

    Returns:
        A PIL.Image object of the generated visualization.
    """
    # If no DataFrame is provided, fetch the data using the kit ID
    if df is None:
        df = get_kit_measurements_df(kit)

    # If data is still unavailable, return a placeholder or raise an error
    if df is None or df.empty:
        raise ValueError(f"No data available for kit {kit}")

    # --- Data cleaning and pivoting ---
    # Drop columns that are not needed for the visualization
    df.drop(columns=['kit_id', "unit", "_raw"], inplace=True, errors='ignore')
    df.dropna(inplace=True)
    
    # Ensure the index is a datetime object before pivoting
    if not isinstance(df.index, pd.DatetimeIndex):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
    df = df.pivot(columns='sensor', values='value')

    # ---- Mapping to polar "Monsoon Mandala" ----
    # Angles map to time; radii encode a blended metric; thickness & dot size encode other variables.
    theta = np.linspace(0, 2 * np.pi, len(df), endpoint=False)

    # Normalize helpers (avoid specifying colors, per instructions).
    def norm(x):
        x = np.asarray(x)
        if np.nanmax(x) - np.nanmin(x) == 0:
            return np.zeros_like(x)
        return (x - np.nanmin(x)) / (np.nanmax(x) - np.nanmin(x))

    T = norm(df['ftTemp'].values)
    H = norm(df['gbHum'].values)
    R = norm(df['NH3'].values)
    W = norm(df['C3H8'].values)
    L = norm(df['CO'].values)

    # Radius combines temp (outer breathing), humidity (inner swell), light (diurnal bloom)
    radius = 0.45 + 0.35*(0.5*T + 0.3*H + 0.2*L)

    # Stroke width from wind; point size from rainfall intensity
    stroke = 0.3 + 3.2*W
    dots = 5 + 60*R

    # Rolling medians for smooth rings
    def smooth(x, k=21):
        if k < 3: 
            return x
        w = np.ones(k)/k
        return np.convolve(x, w, mode="same")

    radius_smooth = smooth(radius, k=31)

    # ---- Plot (no explicit colors; uses matplotlib defaults) ----
    fig = plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, projection="polar")
    ax.set_theta_direction(-1)         # clockwise
    ax.set_theta_offset(np.pi/2.0)     # start at top
    ax.set_axis_off()

    # Outer ribbon
    ax.plot(theta, radius_smooth, linewidth=2.0)

    # Inner filigree rings
    for k in [3, 7, 13]:
        ax.plot(theta, smooth(radius * (0.85 + 0.05*np.sin(k*theta)), k=15), linewidth=0.8)

    # Rainfall pearls
    ax.scatter(theta[::3], (radius_smooth*0.92)[::3], s=dots[::3], alpha=0.6)

    # Wind tick marks (radial sticks)
    for th, rr, sw in zip(theta[::12], radius_smooth[::12], stroke[::12]):
        ax.plot([th, th], [rr*0.75, rr*0.98], linewidth=sw*0.12, alpha=0.8)

    plt.tight_layout()

    # Render figure to RGBA buffer and convert to PIL.Image
    canvas = FigureCanvas(fig)
    canvas.draw()
    buf = np.asarray(canvas.buffer_rgba())
    pil_img = Image.fromarray(buf, mode="RGBA").convert("RGB")

    # Optionally also save to disk for compatibility with other tools
    if save_to_disk:
        png_path = "output/monsoon_mandala_example.png"
        svg_path = "output/monsoon_mandala_example.svg"
        try:
            os.makedirs(os.path.dirname(png_path), exist_ok=True)
            fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.05)
            fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.05)
        except Exception:
            # If saving fails (e.g., directory missing), continue returning the PIL image
            pass

    plt.close(fig)
    return pil_img


if __name__ == "__main__":
    # Example: Generate visualization for a specific kit and save it
    img = weather_data_visualisation(kit=1001, save_to_disk=True)
    if img:
        print("Visualization generated and saved to 'output/'.")
        img.show()  # Display the image