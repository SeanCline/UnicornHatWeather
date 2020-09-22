#!/usr/bin/env python3
from PIL import Image, ImageChops
import colorsys

def open_char_image(character : str):
    if len(character) != 1:
        raise RuntimeError('Not a character.')
    return Image.open(f'characters/{ord(character)}.gif').convert('RGB')


def draw_msg_on_image(base_img, msg : str, x : int, y : int, padding : int = 1):
    img = base_img.copy()
    for c in msg:
        char_img = open_char_image(c)
        img.paste(char_img, (x, y))
        x += char_img.size[0] + padding
    return img


def clamp(val, low, high):
    return max(min(val, high), low)


def interpolate(x : float, src_range, dest_range):
    frac = x / (src_range[1] - src_range[0])
    return dest_range[0] + frac * (dest_range[1] - dest_range[0])


def tempertature_to_color(temperature : float):
    temp = clamp(temperature, 32, 100)
    hue = interpolate(temp, (32, 100), (0, .68))
    color = colorsys.hsv_to_rgb(1-hue, 1.0, 1.0)
    return (int(color[0]*255), int(color[1]*255), int(color[2]*255), int(1*255))


def apply_temperature_tint_to_image(base_img, tempurature : int):
    print(tempertature_to_color(tempurature))
    filter_img = Image.new('RGB', (base_img.width, base_img.height), tempertature_to_color(tempurature))
    return ImageChops.multiply(base_img, filter_img)


def create_temperature_image(temperature : int):
    temp_str = str(temperature).zfill(2)

    # If the string is tool long to draw, then show a different icon.
    if len(temp_str) > 2:
        img = Image.open('icons/cold.gif') if (temperature < 0) else Image.open('icons/hot.gif')
        return img.convert('RGB')
    
    # Draw the temperature on top of the base image.
    img = Image.open('icons/degree_background.gif').convert('RGB')
    img = draw_msg_on_image(img, temp_str, 0, 3)
    img = apply_temperature_tint_to_image(img, temperature)
    
    return img


if __name__ == "__main__":
    # Run through a demonstration of how various colors render.
    create_temperature_image(-10).show()
    create_temperature_image(-9).show()
    create_temperature_image(0).show()
    create_temperature_image(10).show()
    create_temperature_image(20).show()
    create_temperature_image(30).show()
    create_temperature_image(40).show()
    create_temperature_image(50).show()
    create_temperature_image(60).show()
    create_temperature_image(70).show()
    create_temperature_image(80).show()
    create_temperature_image(90).show()
    create_temperature_image(99).show()
    create_temperature_image(100).show()
 