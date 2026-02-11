#!/usr/bin/env python3
import os, time, asyncio
from typing import List
from dataclasses import dataclass
import temperature_image, config
from WeatherCollectors.WeatherCollector import WeatherStatus
from WeatherCollectors.OpenWeatherMapCollector import OpenWeatherMapCollector
from WeatherCollectors.TempestUdpCollector import TempestUdpCollector
from WeatherCollectors.AggregateCollector import AggregateCollector
from WeatherCollectors.TempestCloudCollector import TempestCloudCollector

@dataclass
class GifFrame:
    """Represents Gif, shown for a period of time."""
    filename: str
    show_time: float

def convert_c_to_unit(temp_c: float, unit: str) -> float:
    """Converts a temperature in Celsius to the given unit ('C' or 'F')."""
    if unit == 'C':
        return temp_c
    elif unit == 'F':
        return (temp_c * 9.0 / 5.0) + 32.0
    else:
        raise ValueError(f'Unknown temperature unit: {unit}')

def get_weather_images(collector : WeatherStatus) -> List[GifFrame]:
    """Returns a list of images filenames that fit the current weather conditions."""
    
    # Condition icon.
    if collector.openweathermap_icon is not None:
        conditions_icon_path = os.path.join('./icons/', collector.openweathermap_icon.value + '.gif')
    else:
        conditions_icon_path = './icons/error.gif' 
    
    # Temperature image.
    temperature_image_path = None
    if collector.temp_c is not None:
        cur_temp = round(convert_c_to_unit(collector.temp_c.value, config.tempurature_unit))

        # Create cache file if it doesn't already exist.
        temperature_image_path = os.path.join(config.cache_dir, str(cur_temp) + '.gif')
        if not os.path.exists(temperature_image_path):
            if not os.path.exists(config.cache_dir):
                os.mkdir(config.cache_dir)
                
            # Put the image in the cache.
            print('Creating new image. image=', temperature_image_path)
            img = temperature_image.create_temperature_image(cur_temp)
            img.save(temperature_image_path)
    
    # Build the list of icons to show.
    icons = []
    if conditions_icon_path is not None:
        icons.append(GifFrame(conditions_icon_path, config.condition_show_time))
    
    if temperature_image_path is not None:
        icons.append(GifFrame(temperature_image_path, config.temperature_show_time))

    return icons

async def terminate_proc(proc, graceful_timeout=5):
    if proc is None:
        return
    
    proc.terminate()
    try:
        await asyncio.wait_for(proc.communicate(), timeout=graceful_timeout)
    except asyncio.TimeoutError:
        print('Process took too long to exit. Killing process.')
        proc.kill()
    proc = None

async def show_frames(frames: List[GifFrame]):
    """Loops over the frames and shows each for the given show time."""
    global proc
    try:
        for frame in frames:
            print('Displaying:', frame.filename, 'Time:', frame.show_time)
            await terminate_proc(proc)
            proc = await asyncio.create_subprocess_exec(
                './Gif2UnicornHat/Gif2UnicornHat',
                '-d', config.hat_device,
                frame.filename,
                str(config.image_brightness),
                str(config.image_orientation))
            await asyncio.sleep(frame.show_time)
    except Exception as ex:
        print('Error updating display:', ex)
        await asyncio.sleep(config.retry_time)


async def main():
    """Entrypoint for the program."""
    global proc
    proc = None
    frames = []

    def update_frames(status : WeatherStatus):
        print(status)
        frames.clear()
        frames.extend(get_weather_images(status))

    # Set up all the weather collectors that are configured.
    subCollectors = []

    if hasattr(config, 'tempest_udp_config'):
        subCollectors.append(TempestUdpCollector(config.tempest_udp_config))

    if hasattr(config, 'owm_config') and hasattr(config, 'owm_poll_interval'):
        subCollectors.append(OpenWeatherMapCollector(config.owm_config, config.owm_poll_interval))

    if  hasattr(config, 'tempest_cloud_station_name') and hasattr(config, 'tempest_cloud_token') and hasattr(config, 'tempest_cloud_poll_interval'):
        subCollectors.append(TempestCloudCollector(config.tempest_cloud_station_name, config.tempest_cloud_token, config.tempest_cloud_poll_interval))

    aggregateCollector = AggregateCollector(subCollectors)

    # Register a callback to update the images when new weather data is received.
    aggregateCollector.register_callback(lambda status: update_frames(status))
    listenTask = asyncio.create_task(aggregateCollector.listen()) # Run the collector as a background task.

    while True:
        try:
            # Loop over and display the latest images.
            latest_frames = frames if len(frames) > 0 else [GifFrame('./icons/error.gif', config.retry_time)]
            await show_frames(latest_frames)
        except KeyboardInterrupt:
            print('Exiting...')
            break
        except Exception as ex:
            print('Error updating weather:', ex)
            frames.clear() # Let the user know something went wrong by displaying the error icon on the next loop.

    # Cancel the listener and wait for it to clean up.    
    listenTask.cancel()
    try:
        await listenTask
    except asyncio.CancelledError:
        pass

    # Stop the image diplay.
    await terminate_proc(proc)

if __name__ == '__main__':
    asyncio.run(main())

#from PIL import Image
#if __name__ == "__main__":
#    frames = get_weather_images()
#    for frame in frames:
#        img = Image.open(frame.filename)
#        img.show()
