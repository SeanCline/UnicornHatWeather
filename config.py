# Weather configuration parameters. See: https://openweathermap.org/current
weather_config = {
    'appid': 'YOUR_OPENWEATHERMAP_API_KEY',
    'units': 'imperial', # 'imperial' or 'metric'
    'zip': '44094', # zip code
    
# If in a region without a zip code, comment the zip line above and uncomment one of the following:
    # 'q': 'Willoughby, OH, USA',
    # 'lat': '41.63', 'lon': '-81.41',
}

# Control which temperatures will be displayed cold (blue) and hot (red).
cold_temperature = 32 # If Celsius, 0 is a decent choice. If Fahrenheit, 32.
hot_tempertature = 99 # If Celsius, 38 is a decent choice. If Fahrenheit, 99.

weather_update_time = 300 # Seconds until refreshing weather data.
image_time = 20 # Seconds to display each image.
image_brightness = .02 # Brightness to display the images. 0.0 to 1.0
image_orientation = 0 # Rotates the image so the device can be mounted in a rotated orientation. Values: 0, 1, 2, or 3.
cache_dir = './temperature_images/' # Define an image cache that will be used to keep from re-generating gifs.
