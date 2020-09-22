#!/usr/bin/env python3
import os, time, subprocess, atexit
import weather_conditions, temperature_image, config
from typing import List


# Returns a list of images filenames that fit the current weather conditions.
def get_weather_images() -> List[str]:
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


# Keep track of the currently open process so we can exit gracefully.
proc = None
def cleanup():
    global proc
    if proc is not None:
        proc.terminate()
        proc = None

atexit.register(cleanup)


def main():
    global proc
    while True:
        images_paths = get_weather_images()
        
        # Loop over and display the images.
        for image in images_paths:
            print('Displaying:', image, 'Time:', config.image_time)
            if proc is not None:
                proc.terminate()
            proc = subprocess.Popen(['./Gif2UnicornHat/Gif2UnicornHat', image, config.image_brightness, config.image_orientation])
            time.sleep(config.image_time)


if __name__ == "__main__":
    main()


#from PIL import Image
#if __name__ == "__main__":
#    images_paths = get_weather_images()
#    for path in images_paths:
#        img = Image.open(path)
#        img.show()
    