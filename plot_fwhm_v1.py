import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import os

# --- CONFIGURATION ---
DATA_DIR = "/home/hp/iraf-2.18.1/7jan2026" # Replace with the path name of the directory where the csv file is present.
CSV_FILE = os.path.join(DATA_DIR, "live_M34_fwhm_data .csv")
SAVE_IMAGE_FILE = os.path.join(DATA_DIR, "fwhm_focus_M34_new_monitor.png") 
FOCUS_COLUMN = 'FOCUS'  # Change this if your column name is different

# Setup the plot style
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(10, 5))

def animate(i):
    if not os.path.exists(CSV_FILE):
        ax.clear()
        ax.text(0.5, 0.5, "Waiting for data...", ha='center', color='yellow')
        return

    try:
        # Read the CSV
        df = pd.read_csv(CSV_FILE)

        if df.empty or FOCUS_COLUMN not in df.columns:
            ax.clear()
            ax.text(0.5, 0.5, f"Column '{FOCUS_COLUMN}' not found", ha='center', color='red')
            return

        # Sort by focus value to ensure the line connects points in order
        df = df.sort_values(by=FOCUS_COLUMN)

        # Clear and redraw
        ax.clear()

        # Plot FWHM (Arcsec) vs Focus
        ax.plot(df[FOCUS_COLUMN], df['FWHM_ARCSEC'], 'o-', color='#00ff00', 
                linewidth=2, markersize=6, label='FWHM (arcsec)')

        # Formatting
        ax.set_title(f"Focus vs FWHM (N={len(df)})", fontsize=14, color='white')
        ax.set_xlabel("Focus Value", fontsize=12)
        ax.set_ylabel("FWHM (arcsec)", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(loc='upper right')

        # Add current/last added value text
        # Since we sorted by Focus, we find the last entry from the original CSV to highlight
        last_row = pd.read_csv(CSV_FILE).iloc[-1]
        ax.text(last_row[FOCUS_COLUMN], last_row['FWHM_ARCSEC'] + 0.1, 
                f"{last_row['FWHM_ARCSEC']:.2f}\"", color='cyan', fontweight='bold')

        # Save the plot
        fig.savefig(SAVE_IMAGE_FILE)

    except Exception as e:
        print(f"Error plotting: {e}")

# Update every 3 seconds
ani = animation.FuncAnimation(fig, animate, interval=3000)

plt.tight_layout()
plt.show()
