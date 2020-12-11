#!/usr/bin/env python3
import urllib.request, urllib.parse, json
from dataclasses import dataclass
from datetime import datetime, timezone


def get_weather_url(weather_config : dict):
    """Use the configuration parameters to generate the request URL."""
    return 'https://api.openweathermap.org/data/2.5/weather?' + urllib.parse.urlencode(weather_config)



@dataclass
class WeatherConditions(object):
    """Describes a set of weather conditions at a particular point in time."""
    temperature: float
    pressure: float
    humidity: float
    weather: str
    icon: str
    time: datetime


def get_current_weather_conditions(weather_config) -> WeatherConditions:
    """Retrieves the current WeatherConditions from the web."""
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
