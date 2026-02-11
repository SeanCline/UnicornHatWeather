#!/usr/bin/env python3
import asyncio, aiohttp
from typing import Optional
from datetime import datetime, timezone
from .WeatherCollector import WeatherCollector, WeatherStatus, Datapoint

class TempestCloudCollector(WeatherCollector):
    """Collects weather data from Weatherflow's REST API. https://weatherflow.github.io/Tempest/api/"""

    def __init__(self, station_name : str, token : str, poll_interval : float = 300.0):
        super().__init__()
        self._station_name = station_name
        self._token = token
        self._poll_interval = poll_interval
        self._is_listening = False

    def _get_observation_url(self):
        """Use the configuration parameters to generate the request URL."""
        return f'https://swd.weatherflow.com/swd/rest/observations/station/{self._station_name}?token={self._token}'
    
    def _get_forecast_url(self):
        """Use the configuration parameters to generate the request URL."""
        return f'https://swd.weatherflow.com/swd/rest/better_forecast?station_id={self._station_name}&token={self._token}'

    def _decode_precipitation(self, v) -> str:
        """Converts the Weatherflow precipitation type code to a human readable string."""
        return {0: "none", 1: "rain", 2: "hail", 3: "hail"}.get(v) or "none" # 3 == rain|hail, but it's experimental and rare, so just call it hail.

    def _decode_icon(self, icon_name : str, illuminance_lux : Optional[float]) -> Optional[str]:
        """Converts the Weatherflow icon code to a the icon codes used by OpenWeatherMap."""
        daynight = 'd' if illuminance_lux is None or illuminance_lux > 100 else 'n'
        mapping = {
            'clear-day': '01d',
            'clear-night': '01n',
            'cloudy': '03' + daynight,
            'foggy': '50' + daynight,
            'partly-cloudy-day': '02d',
            'partly-cloudy-night': '02n',
            'possibly-rainy-day': '09d',
            'possibly-rainy-night': '09n',
            'possibly-sleet-day': '09d',
            'possibly-sleet-night': '09n',
            'possibly-snow-day': '13d',
            'possibly-snow-night': '13n',
            'possibly-thunderstorm-day': '11d',
            'possibly-thunderstorm-night': '11n',
            'rainy': '10' + daynight,
            'sleet': '10' + daynight,
            'snow': '50' + daynight,
            'thunderstorm': '11' + daynight,
            'windy': '02' + daynight, # OWM doesn't have a windy icon, so just show it as partly cloudy.
        }
        return mapping.get(icon_name, None)

    async def _get_current_weather_conditions(self) -> WeatherStatus:
        """Retrieves the current WeatherConditions from the web."""
        
        # Request both the observations (current conditions) and the forecast at the same time.
        async with aiohttp.ClientSession() as session:
            obs_response, forecast_response = await asyncio.gather(
                session.get(self._get_observation_url()),
                session.get(self._get_forecast_url()),
            )

            # Await both REST responses before processing them.
            async with obs_response:
                obs_body = await obs_response.json()
            async with forecast_response:
                forecast_body = await forecast_response.json()

        status = WeatherStatus()
        status.source = "tempest_cloud"
        status.host_timestamp = datetime.now(timezone.utc)

        if obs_body is not None and int(obs_body.get('status', {}).get('status_code', -1)) == 0:
            obs = obs_body['obs'][0] # Get the most recent observation.

            # Most qualities are set to 0.5-0.75 since it's a local station, but not a direct connection like the UDP API.
            if 'timestamp' in obs:
                status.source_timestamp = datetime.fromtimestamp(obs['timestamp'], timezone.utc)

            if 'air_temperature' in obs:
                status.temp_c = Datapoint(obs['air_temperature'], 0.75)

            if 'relative_humidity' in obs:
                status.humidity_pct = Datapoint(obs['relative_humidity'], 0.75)

            if 'barometric_pressure' in obs:
                status.pressure_mb = Datapoint(obs['barometric_pressure'], 0.75)

            if 'brightness' in obs:
                status.illuminance_lux = Datapoint(obs["brightness"], .5)

            if 'uv' in obs:
                status.uv_index = Datapoint(obs["uv"], .5)

            if 'wind_avg' in obs:
                status.wind_avg_mps = Datapoint(obs['wind_avg'], .5)
            
            if 'precip' in obs:
                status.precip_type = Datapoint(self._decode_precipitation(obs['precip']), 0.5)

            if 'precip_accum_last_1hr' in obs:
                status.rain_mm = Datapoint(obs['precip_accum_last_1hr'] / 60, 0.75) # More averaged than the UDP API, so less noisy.
            
            if 'lightning_strike_count' in obs:
                status.lightning_count = Datapoint(obs["lightning_strike_count"], .75)
            
            if status.lightning_count is not None and status.lightning_count.value > 0:
                status.lightning_distance = Datapoint(obs["lightning_strike_last_distance"], .75)

        if forecast_body is not None and int(forecast_body.get('status', {}).get('status_code', -1)) == 0:
            current_conditions = forecast_body['current_conditions']

            if 'conditions' in current_conditions:
                status.condition_string = Datapoint(current_conditions['conditions'], 0.25) # More reliable than a local guess, but still just a guess.

            icon = self._decode_icon(current_conditions['icon'], status.illuminance_lux.value if status.illuminance_lux else None)
            if icon is not None:
                status.openweathermap_icon = Datapoint(icon, 0.25)
         
        return status
    
    async def listen(self):
        """Starts polling for weather updates. This will run until cancelled."""

        while True:
            try:
                status = await self._get_current_weather_conditions()
                self._deliver_update(status)
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                raise # Propagate task cancellations to the awaiter.
            except Exception as e:
                print(f'Error getting weather data: {e}') # Suppress other types of exception.

async def debug_status():
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
    import config

    collector = TempestCloudCollector(config.tempest_cloud_station_name, config.tempest_cloud_token, config.tempest_cloud_poll_interval)
    collector.register_callback(lambda status: print(status))
    await collector.listen() # Run forever for debugging.

if __name__ == "__main__":
    ws = WeatherStatus()
    asyncio.run(debug_status())
