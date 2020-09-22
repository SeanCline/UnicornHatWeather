
# Weather configuration parameters.
weather_config = {
    'api_key': 'YOUR_API_KEY',
    'zip_code': '44094',
    'units': 'imperial',
}

weather_update_time = 300 # Seconds until refreshing weather data.
image_time = 20 # Seconds to display each image.
image_brightness = '.02' # Brightness to display the images. 0.0 to 1.0
image_orientation = '0' # Rotates the image so the device can be mounted in a rotated orientation. Values: 0, 1, 2, or 3.
cache_dir = './temperature_images/' # Define an image cache that will be used to keep from re-generating gifs.
