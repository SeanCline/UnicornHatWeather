#!/usr/bin/env python3
import os, time, subprocess, atexit
import weather_conditions, temperature_image, config
from typing import List
from dataclasses import dataclass

@dataclass
class GifFrame:
    """Represents Gif, shown for a period of time."""
    filename: str
    show_time: float

def get_weather_images() -> List[GifFrame]:
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
        print('Creating new image. image=', temperature_image_path)
        img = temperature_image.create_temperature_image(cur_temp)
        img.save(temperature_image_path)
    
    return [
        GifFrame(conditions_icon_path, config.condition_show_time),
        GifFrame(temperature_image_path, config.temperature_show_time),
    ]

def terminate_proc(proc, graceful_timeout=5000):
    if proc is None:
        return
    
    proc.terminate()
    try:
        outs, errs = proc.communicate(timeout=graceful_timeout)
    except subprocess.TimeoutExpired:
        print('Process took took long to exit. Killing process.')
        proc.kill()

# Register a cleanup function that terminates subprecesses.
proc = None
def cleanup():
    """Keep track of the currently open process so we can exit gracefully."""
    global proc
    terminate_proc(proc)
    proc = None

atexit.register(cleanup)


def show_frames(frames: List[GifFrame]):
    """Loops over the frames and shows each for the given show time."""
    global proc
    try:
        for frame in frames:
            print('Displaying:', frame.filename, 'Time:', frame.show_time)
            terminate_proc(proc)
            proc = subprocess.Popen(['./Gif2UnicornHat/Gif2UnicornHat',
                '-d', config.hat_device,
                frame.filename,
                str(config.image_brightness),
                str(config.image_orientation)])
            time.sleep(frame.show_time) # Sleep while the image is displayed.
    except Exception as ex:
        print('Error updating display:', ex)
        time.sleep(config.retry_time) # Don't update too fast on error.


def main():
    """Entrypoint for the program."""
    last_update_time = float('-inf')
    frames = []
    
    while True:
        # Update the image list if the weather_update_time has passed.
        try:
            if (time.monotonic() - last_update_time) >= config.weather_update_time:
                frames = get_weather_images()
                last_update_time = time.monotonic()
        except Exception as ex:
            print('Error updating weather:', ex)
            # Let the user know something went wrong.
            frames = [GifFrame('./icons/error.gif', config.retry_time)]
        
        # Loop over and display the images.
        show_frames(frames)


if __name__ == '__main__':
    main()


#from PIL import Image
#if __name__ == "__main__":
#    frames = get_weather_images()
#    for frame in frames:
#        img = Image.open(frame.filename)
#        img.show()
    