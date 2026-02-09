# OpenWeatherMap configuration parameters. See: https://openweathermap.org/current
owm_config = {
    'appid': 'YOUR_OPENWEATHERMAP_API_KEY',
    'zip': '44060', # zip code
    
# If in a region without a zip code, comment the zip line above and uncomment one of the following:
    # 'q': 'Willoughby, OH, USA',
    # 'lat': '41.63', 'lon': '-81.41',
}
owm_poll_interval = 300.0 # Seconds between refreshing weather data.

# Control how tempuratures will be displayed and which temps map to cold (blue) and hot (red).
tempurature_unit = 'F' # 'C' for Celsius, 'F' for Fahrenheit.
cold_temperature = 32 # If Celsius, 0 is a decent choice. If Fahrenheit, 32.
hot_tempertature = 99 # If Celsius, 38 is a decent choice. If Fahrenheit, 99.

condition_show_time = 10.0 # Seconds to display the condition icon.
temperature_show_time = 15.0 # Seconds to display the temperature icon.
retry_time = 15.0 # Seconds to wait before retrying when there's an error.
image_brightness = .02 # Brightness to display the images. 0.0 to 1.0
image_orientation = 0 # Rotates the image so the device can be mounted in a rotated orientation. Values: 0, 1, 2, or 3.
hat_device = 'Unicorn HAT' # Which LED matrix is connected. Options: 'Unicorn HAT' or 'Unicorn HAT HD'
cache_dir = './temperature_images/' # Define an image cache that will be used to keep from re-generating gifs.
leading_zero_char = ' ' # Set to '0' for temperatures to always be 2 digits.