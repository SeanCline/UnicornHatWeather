UnicornHatWeather
==============

Displays the current weather conditions on a [Pimoroni UnicornHat](https://shop.pimoroni.com/products/unicorn-hat).

# Installation #
These instructions assume a fresh installation of [Raspberry Pi OS Buster](https://www.raspberrypi.org/downloads/raspberry-pi-os/).

## Install dependencies ##
	sudo apt install build-essential git libgif-dev scons python python3-pip libopenjp2 libtiff5

## Clone and build ##

	cd ~
	git clone --recursive https://github.com/SeanCline/UnicornHatWeather.git
	cd UnicornHatWeather/Gif2UnicornHat
	make dependencies && make
	cd ..
	sudo pip3 install -r requirements.txt

## Configuration ##
Open `config.py`
Update the your zipcode.
Set your [OpenWeatherMap API key](https://openweathermap.org/appid).

# Usage #
	sudo ./UnicornHatWeather.py
