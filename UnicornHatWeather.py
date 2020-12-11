#!/usr/bin/env python3
import os, time, subprocess, atexit
import weather_conditions, temperature_image, config
from typing import List


def get_weather_images() -> List[str]:
    """Returns a list of images filenames that fit the current weather conditions."""
    # Get the current conditions.
    conditions = weather_conditions.get_current_weather_conditions(config.weather_config)
    print(conditions)
    
    # Condition icon.
    conditions_icon_path = os.path.join('./icons/', conditions.icon + '.gif')
    
    # Temperature image.
    cur_temp = round(conditions.temperature)
    
    # Create cache file if it doesn't already exist.
    temperature_image_path = os.path.join(config.cache_dir, str(cur_temp) + '.gif')
    if not os.path.exists(temperature_image_path):
        if not os.path.exists(config.cache_dir):
            os.mkdir(config.cache_dir)
            
        # Put the image in the cache.
        print("Creating new image. image=", temperature_image_path)
        img = temperature_image.create_temperature_image(cur_temp)
        img.save(temperature_image_path)
    
    return [conditions_icon_path, temperature_image_path]

# Register a cleanup function that terminates subprecesses.
proc = None
def cleanup():
    """Keep track of the currently open process so we can exit gracefully."""
    global proc
    if proc is not None:
        proc.terminate()
        proc = None

atexit.register(cleanup)


def main():
    """Entrypoint for the program."""
    global proc
    last_update_time = float('-inf')
    image_paths = []
    
    while True:
        # Update the image list if the weather_update_time has passed.
        try:
            if (time.monotonic() - last_update_time) >= config.weather_update_time:
                image_paths = get_weather_images()
                last_update_time = time.monotonic()
        except Exception as ex:
            print("Error updating weather:", ex)
            image_paths = ['./icons/error.gif'] # Let the user know something went wrong.
            time.sleep(config.image_time) # Don't update too fast on error.
        
        # Loop over and display the images.
        try:
            for image in image_paths:
                print('Displaying:', image, 'Time:', config.image_time)
                if proc is not None:
                    proc.terminate()
                proc = subprocess.Popen(['./Gif2UnicornHat/Gif2UnicornHat', image, str(config.image_brightness), str(config.image_orientation)])
                time.sleep(config.image_time) # Sleep while the image is displayed.
        except Exception as ex:
            print("Error updating display:", ex)
            time.sleep(config.image_time) # Don't update too fast on error.

if __name__ == "__main__":
    main()


#from PIL import Image
#if __name__ == "__main__":
#    image_paths = get_weather_images()
#    for path in image_paths:
#        img = Image.open(path)
#        img.show()
    