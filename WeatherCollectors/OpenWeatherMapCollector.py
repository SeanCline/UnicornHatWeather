#!/usr/bin/env python3
import asyncio, aiohttp, urllib.parse
from datetime import datetime, timezone
from .WeatherCollector import WeatherCollector, WeatherStatus, Datapoint

class OpenWeatherMapCollector(WeatherCollector):
    """Collects weather data from OpenWeatherMap."""

    def __init__(self, config : dict, poll_interval : float = 300.0):
        super().__init__()
        self._config = config
        self._poll_interval = poll_interval
        self._is_listening = False

        # Force units to metric so we can convert to the units specified in config.py ourselves.
        self._config['units'] = 'metric'

    def _get_weather_url(self):
        """Use the configuration parameters to generate the request URL."""
        return 'https://api.openweathermap.org/data/2.5/weather?' + urllib.parse.urlencode(self._config)
    
    async def _get_current_weather_conditions(self) -> WeatherStatus:
        """Retrieves the current WeatherConditions from the web."""
        
        url = self._get_weather_url()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                body = await response.json()

        if int(body['cod']) == 200:
            main = body.get('main', {})
            wind = body.get('wind', {})
            weather = body.get('weather', [{}])[0] # Only interested in the primary weather object.

            status = WeatherStatus()
            status.source = "openweathermap"
            status.host_timestamp = datetime.now(timezone.utc)

            if 'dt' in body:
                status.source_timestamp = datetime.fromtimestamp(body['dt'], timezone.utc)

            if 'temp' in main:
                status.temp_c = Datapoint(main['temp'], 0.5) # Quality is good, but not as good as a local sensor.

            if 'humidity' in main:
                status.humidity_pct = Datapoint(main['humidity'], 0.5)
            
            if 'pressure' in main:
                status.pressure_mb = Datapoint(main['pressure'], 0.5)

            if 'speed' in wind:
                status.wind_avg_mps = Datapoint(wind['speed'], .75) # I trust the OWM wind speed more than a ground-mounted sensor.
            
            if 'description' in weather:
                status.condition_string = Datapoint(weather['description'], 1.0) # Real weather services use FAR more reliable models for conditions than a local sensor.

            if 'icon' in weather:
                status.openweathermap_icon = Datapoint(weather['icon'], 1.0)
            
            # Determine if it's precipitating based on the weather code.
            # See: https://openweathermap.org/weather-conditions
            if 'id' in weather:
                id = weather['id']
                precip_type = ("rain" if id >= 200 and id < 400
                    else "rain" if id >= 500 and id < 600
                    else "snow" if id >= 600 and id < 700
                    else None)
                if precip_type is not None:
                    quality = 0.0 if precip_type == "rain" else 0.75 # The rain values are worse than a local station, but snow is better.
                    status.precip_type = Datapoint(precip_type, quality)

                if 'rain' in body and '1h' in body['rain']:
                    status.precip_type = Datapoint('rain', 0.75)
                    status.rain_mm = Datapoint(body['rain']['1h'], 0.75)

            return status
        else:
            raise RuntimeError(f'Weather query failed. {body["cod"]} - {body["message"]}')
    
    async def start_listening(self):
        """Starts polling for weather updates. This will run until stop_listening is called.."""
        if self._is_listening:
            return # Already listening.
        
        self._is_listening = True
        while self._is_listening:
            try:
                status = await self._get_current_weather_conditions()
                self._deliver_update(status)
            except Exception as e:
                print('Error getting weather data:', e)
            await asyncio.sleep(self._poll_interval)

    async def stop_listening(self):
        """Stops polling for updates. Call this to clean up resources and stop collecting data."""
        self._is_listening = False

async def debug_status():
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
    import config

    collector = OpenWeatherMapCollector(config.owm_config, config.owm_poll_interval)
    collector.register_callback(lambda status: print(status))
    await collector.start_listening()
    
    # Run until a keyboard interrupt, then clean up.
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        pass
    await collector.stop_listening()

if __name__ == "__main__":
    ws = WeatherStatus()
    asyncio.run(debug_status())
