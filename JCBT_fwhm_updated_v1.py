import astropy.io.fits as pyfits
import matplotlib as mpl
import astropy.units as u
from astropy.table import Table, Column 
from matplotlib.gridspec import GridSpec as GR
from photutils.aperture import CircularAperture
import sep
from scipy.ndimage import maximum_filter
import sys
from io import StringIO
from pyraf import iraf
import pyds9
import pandas as pd
import glob
import os
import time
import re
import numpy as np
from astropy.wcs import WCS
import shutil

# --- CONFIGURATION ---
SOURCE_DIR = "/mnt/focus_testing_8jan_1" # Replace with the path name of your remote folder. 
LOCAL_DIR = "/home/hp/iraf-2.18.1/8jan2026_1" # Replace with the path name of your local directory where the remote files are to be copied.
LIVE_DATA_CSV = os.path.join(LOCAL_DIR, "live_fwhm_data.csv") 
TEMP_COO_FILE = os.path.join(LOCAL_DIR, "temp_sources.coo")

SLEEP_INTERVAL = 3
pixel_scale = 0.257

def save_brightest_as_coo(source_table, filename):
    """Save source table as IRAF coordinate file"""
    x_coords = source_table['x']
    y_coords = source_table['y']
    
    with open(filename, 'w') as f:
        for i, (x, y) in enumerate(zip(x_coords, y_coords), 1):
            f.write(f"{x:.2f} {y:.2f}\n")
    return filename

def extract_iraf_fwhm_average(output_text):
    """
    Parses IRAF psfmeasure output to get FWHM and Ellipticity.
    Handles both single-star ('Full width...') and multi-star ('Average full width...') outputs.
    """
    avg_pattern = r'(?:Average full|Full) width at half maximum \(FWHM\) of ([\d.]+)'
    match_avg = re.search(avg_pattern, output_text)
    
    if match_avg:
        avg_fwhm_iraf = float(match_avg.group(1))
        
        # Extract Individual Star Data (Col, Line, Mag, FWHM, Ellip, PA)
        data_pattern = r'(\d+\.\d+)\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-?\d+)'
        matches = re.findall(data_pattern, output_text)
        
        fwhm_values = []
        ellip_values = []
        
        for m in matches:
            try:
                f = float(m[3])
                e = float(m[4])
                fwhm_values.append(f)
                ellip_values.append(e)
            except:
                continue
        
        n_stars = len(fwhm_values)
        avg_ellip = np.mean(ellip_values) if ellip_values else 0.0
        
        if not fwhm_values:
            fwhm_values = [avg_fwhm_iraf]
            n_stars = 1

        return {
            'average_fwhm_pixels': avg_fwhm_iraf,
            'average_ellipticity': avg_ellip,
            'individual_fwhms': np.array(fwhm_values),
            'n_stars': n_stars,
            'average_fwhm_arcsec': avg_fwhm_iraf * pixel_scale
        }
        
    return None

def capture_iraf_output(func, *args, **kwargs):
    """Capture IRAF stdout -> parse average"""
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
        output = captured_output.getvalue()
    
    return extract_iraf_fwhm_average(output)

def main():
    if not os.path.exists(LOCAL_DIR):
        os.makedirs(LOCAL_DIR)

    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory {SOURCE_DIR} not found.")
        return
    
    os.chdir(LOCAL_DIR)
    
    try:
        d = pyds9.DS9()
    except Exception:
        print("Please open DS9 first!")
        return

    print("Initializing IRAF...")
    iraf.images()
    iraf.noao()
    iraf.digiphot() 
    iraf.obsutil()
    
    print(f"Watching {SOURCE_DIR}...")

    try:
        while True:
            source_files = {f for f in os.listdir(SOURCE_DIR) if f.lower().endswith('.fits')}
            local_files = {f for f in os.listdir(LOCAL_DIR) if f.lower().endswith('.fits')}
            new_files = sorted(list(source_files - local_files))

            if new_files:
                print(f"\nFound {len(new_files)} new file(s) {new_files} to process. Proceed? (y/n):")
                user_input = input().strip().lower()
                if user_input != 'y':
                    print("Skipping processing.")
                    continue

                for f in new_files:
                    source_path = os.path.join(SOURCE_DIR, f)
                    local_path = os.path.join(LOCAL_DIR, f)

                    try:
                        print(f"Processing: {f}")
                        time.sleep(0.5) 
                        shutil.copy2(source_path, local_path)
                        print(f" -> Copied to local drive")
                    except Exception as e:
                        print(f"Error copying file: {e}")
                        continue 

                    try:
                        # Use the explicit command string and increase the pause
                        d.set(f'file {local_path}')
                        time.sleep(2)  # Give DS9 more time to allocate memory for the file
                        d.set('scale zscale')
                        time.sleep(1)

                        with pyfits.open(local_path) as hdul:
                            header = hdul[0].header
                            focus = header.get('TELFOCUS')

                            img_data = hdul[0].data
                            if len(img_data.shape) == 3:
                                img_2d = img_data[0].astype(np.float32)
                            else:
                                img_2d = img_data.astype(np.float32)

                            bkg = sep.Background(img_2d)
                            thresh = bkg.globalback + 3.0 * bkg.globalrms
                            img_clean = img_2d - bkg

                            neighborhood_size = 11
                            local_maxima = maximum_filter(img_clean, size=neighborhood_size) == img_clean
                            peaks = np.argwhere(local_maxima & (img_clean > thresh))
                            sources_xy = peaks[:, [1, 0]]
                            fluxes = img_clean[peaks[:, 0], peaks[:, 1]]

                            print(f" -> Sources detected: {len(sources_xy)}")

                            if len(sources_xy) == 0:
                                print(" -> No stars found. Skipping IRAF.")
                                continue

                            source_table = Table()
                            source_table['x'] = sources_xy[:, 0] + 1
                            source_table['y'] = sources_xy[:, 1] + 1
                            source_table['flux'] = fluxes

                            source_table1 = source_table[source_table['flux'] < 100000]
                            brightest_15 = source_table1[np.argsort(source_table1['flux'])[::-1][:15]]

                            save_brightest_as_coo(brightest_15, filename=TEMP_COO_FILE)
                        
                        results = capture_iraf_output(
                            iraf.psfmeasure, 
                            f, 
                            display="no",           
                            scale=1, 
                            radius=10,             
                            coords="markall",       
                            imagecur=TEMP_COO_FILE, 
                            graphcur="dev$null",   # <--- The fix for the hanging window
                            wcs="logical"
                        )
                        
                        if results:
                            print(f" -> Measured FWHM: {results['average_fwhm_pixels']:.2f} px")
                            
                            new_row = {
                                'FILENAME': f,
                                'FOCUS': focus,
                                'FWHM_PIX': results['average_fwhm_pixels'],
                                'FWHM_ARCSEC': results['average_fwhm_arcsec'],
                                'N_STARS': results['n_stars']
                            }
                            
                            if not os.path.exists(LIVE_DATA_CSV):
                                pd.DataFrame([new_row]).to_csv(LIVE_DATA_CSV, index=False)
                            else:
                                pd.DataFrame([new_row]).to_csv(LIVE_DATA_CSV, mode='a', header=False, index=False)
                        else:
                            print(" -> No valid FWHM returned from IRAF.")

                        iraf.imexam()
                        print("Proceed with next file?(y/n):")
                        user_input = input().strip().lower()
                        if user_input != 'y':
                            print("Exiting processing loop.")
                            return

                    except Exception as e:
                        print(f"Skipping {f} - Error processing: {e}")
                        try: iraf.unlearn('psfmeasure') ; iraf.unlearn('imexam')
                        except: pass
                    
            time.sleep(SLEEP_INTERVAL)

    except KeyboardInterrupt:
        print("\nExiting script.")

if __name__ == "__main__":
    main()
