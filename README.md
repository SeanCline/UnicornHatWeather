UnicornHatWeather
==============

Displays the current weather conditions on a [Pimoroni Unicorn HAT](https://shop.pimoroni.com/products/unicorn-hat) or [Unicorn HAT HD](https://shop.pimoroni.com/products/unicorn-hat-hd).

![](docs/night.jpg)
![](docs/night_temp.jpg)

# Installation #
These instructions assume a fresh installation of [Raspberry Pi OS Buster](https://www.raspberrypi.org/downloads/raspberry-pi-os/).

## Install dependencies ##

	sudo apt update
	sudo apt dist-upgrade
	sudo apt install build-essential git libgif-dev scons python python3-pip libopenjp2-7 libtiff5

## Clone and build ##

	cd ~
	git clone --recursive https://github.com/SeanCline/UnicornHatWeather.git
	cd UnicornHatWeather/Gif2UnicornHat
	make dependencies && make
	cd ..
	sudo pip3 install -r requirements.txt

## Configuration ##
 - [Sign up](https://home.openweathermap.org/users/sign_up) for OpenWeatherMap and retrieve your API key from [here](https://home.openweathermap.org/api_keys).
 - Open `config.py` and replace `YOUR_OPENWEATHERMAP_API_KEY` with your API key.
 - Set your city by either updating the zip code or by using one of the other formats for defining your city.

# Usage #
	sudo ./UnicornHatWeather.py

# Automatic startup #
In order to start the weather display whenever the Raspberry Pi is booted, run the following:

	sudo cp gif.service /etc/systemd/system/gif.service
	sudo systemctl daemon-reload
	sudo systemctl enable gif.service
