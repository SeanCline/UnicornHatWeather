UnicornHatWeather
==============

Displays the current weather conditions on a [Pimoroni Unicorn HAT](https://shop.pimoroni.com/products/unicorn-hat) or [Unicorn HAT HD](https://shop.pimoroni.com/products/unicorn-hat-hd).

![](docs/night.jpg)
![](docs/night_temp.jpg)

# Installation #
These instructions assume a fresh installation of [Raspberry Pi OS Trixie](https://www.raspberrypi.org/downloads/raspberry-pi-os/).

## Install dependencies ##

	sudo apt update
	sudo apt full-upgrade
	sudo apt install build-essential git libgif-dev scons python3-full python3-venv python3-pip libopenjp2-7 libjpeg-dev

## Clone and build ##

	cd ~
	git clone --recursive https://github.com/SeanCline/UnicornHatWeather.git
	cd UnicornHatWeather/Gif2UnicornHat
	make dependencies && make
	cd ..
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip setuptools wheel
	.venv/bin/python -m pip install -r requirements.txt

## Configuration ##
### OpenWeatherMap ###
This is the recommended weather collector.
 - [Sign up](https://home.openweathermap.org/users/sign_up) for OpenWeatherMap and retrieve your API key from [here](https://home.openweathermap.org/api_keys).
 - Open `config.py` and replace `YOUR_OPENWEATHERMAP_API_KEY` with your API key.
 - Set your city by either updating the zip code or by using one of the other formats for defining your city.

### WeatherFlow Tempest ###

#### UDP ####
Optionally, if you have a [WeatherFlow Tempest](https://tempest.earth/tempest-home-weather-system/) station, more accurate and up-to-date temperature values can be displayed by enabling the `tempest_udp_*` parameters in `config.py`
The Tempest UDP API is local-only, so while its temperature data is very good, the weather condition icon does not use the more advanced weather models that cloud APIs like OpenWeatherMap or WeatherFlow Tempest's cloud can use. Even with the Tempest UDP API enabled, it's recommended to _also_ configure OpenWeatherMap or the Tempest Cloud API for more accurate current conditions icons.

#### Cloud API ####
If you have a WeatherFlow station, you can 
 - Generate a WeatherFlow Token from [here](https://tempestwx.com/settings/tokens).
 - Open `config.py` and replace `YOUR_TEMPESTWX_API_KEY` with your API key.
 - Configure the rest of the `tempest_cloud_*` configuration settings.

# Usage #
	sudo ./UnicornHatWeather.py

# Automatic startup #
In order to start the weather display whenever the Raspberry Pi is booted, run the following:

	sudo cp gif.service /etc/systemd/system/gif.service
	sudo systemctl daemon-reload
	sudo systemctl enable gif.service
