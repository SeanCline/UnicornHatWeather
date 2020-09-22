#!/usr/bin/env python3
import urllib.request, json
from dataclasses import dataclass
from datetime import datetime, timezone


# Use the configuration parameters to generate the request URL.
def get_weather_url(weather_config : dict):
    return f'https://api.openweathermap.org/data/2.5/weather?appid={weather_config["api_key"]}&zip={weather_config["zip_code"]}&units={weather_config["units"]}'


# Describes a set of weather conditions at a particular point in time.
@dataclass
class WeatherConditions(object):
    temperature: float
    pressure: float
    humidity: float
    weather: str
    icon: str
    time: datetime


# Retrieves the current WeatherConditions from the web.
def get_current_weather_conditions(weather_config) -> WeatherConditions:
    url = get_weather_url(weather_config)
    request = urllib.request.urlopen(url)
    body = json.load(request)

    if int(body['cod']) == 200:
        main = body['main']
        weather = body['weather'][0]
        conditions = WeatherConditions(
            temperature = main['temp'],
            pressure = main['pressure'],
            humidity = main['humidity'],
            weather = weather['main'],
            icon = weather['icon'],
            time = datetime.fromtimestamp(body['dt'], timezone.utc),
        )
        return conditions
    else:
        raise RuntimeError(f'Weather query failed. {body["cod"]} - {body["message"]}')


if __name__ == "__main__":
    conditions = get_current_weather_conditions()
    print(conditions)
