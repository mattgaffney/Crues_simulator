#!/usr/bin/python3

import argparse
import math
import time

import matplotlib.pyplot as plt
from matplotlib import animation
import numpy
import png


class Map:
    def __init__(self, img):
        r = png.Reader(filename=img)
        self.w, self.h, px, _ = r.read_flat()
        ch = int(round(len(px) / (self.w * self.h)))
        self.px = numpy.array(px).reshape((self.h, self.w, ch))

    def is_wall(self, pos):
        return not any((self.is_line(pos), self.is_clear(pos)))

    def is_line(self, pos):
        p = self.px[int(pos.imag)][int(pos.real)]
        return all((p[0] >= 127, p[1] < 127, p[2] < 127))

    def is_clear(self, pos):
        p = self.px[int(pos.imag)][int(pos.real)]
        return all((p[0] >= 127, p[1] >= 127, p[2] >= 127))


steering_factor = 0.01


class Car:
    def __init__(self, pos):
        self.pos = pos
        self.width = 50
        self.length = 80
        self.rot = 0
        self.front_left = complex(-self.width / 2, -self.length / 2)
        self.front_right = complex(self.width / 2, -self.length / 2)
        self.back_left = complex(-self.width / 2, self.length / 2)
        self.back_right = complex(self.width / 2, self.length / 2)
        self.left_sensor = complex(-self.width / 2 - 10, -self.length / 2)
        self.right_sensor = complex(self.width / 2 + 10, -self.length / 2)
        self.front_sensor = complex(0, -self.length / 2 - 10)
        self.back_sensor = complex(0, self.length / 2 + 5)
        self.sensors = (self.front_sensor, self.back_right, self.back_left, self.front_right, self.front_left,
                        self.left_sensor, self.right_sensor)
        self.prefer_left = True
        self.reverse_count = 0
        self.steer_count = 0

    def to_world(self, p):
        """Takes a point relative to the centre of the car (in driving direction) and calculates the world coordinates,
        based on the current position and angle of the car"""
        return self.pos + p * complex(math.cos(self.rot), math.sin(self.rot))

    def move(self, fwd, steer):
        """Update position and angle of car.

        :param fwd: Car moves forward if True, backward if false
        :param steer: In range [-1; 1], -1 is hard left, 1 is hard right, 0 is no change in direction
        """
        self.rot += steer * steering_factor
        if self.rot < -math.pi:
            self.rot += 2*math.pi
        elif self.rot > math.pi:
            self.rot -= 2*math.pi
        self.pos = self.to_world(complex(0, -1 if fwd else 1))


counter = 0


def update_car(map, car):
    if car.reverse_count:  # More reversing to do - go straight back
        if not all([map.is_clear(car.to_world(s)) for s in (car.back_right, car.back_left)]):  # Obstacle behind - stop reversing
            car.reverse_count = 0
            return
        car.move(False, 0)
        car.reverse_count -= 1;
        return
    fs = car.to_world(car.front_sensor)
    frs = car.to_world(car.front_right)
    fls = car.to_world(car.front_left)
    rs = car.to_world(car.right_sensor)
    ls = car.to_world(car.left_sensor)
    if not all([map.is_clear(x) for x in [fs, frs, fls]]):  # Obstacle on emergency brake sensor
        if map.is_clear(fs) and map.is_clear(frs):
            car.prefer_left = False
        elif map.is_clear(fs) and map.is_clear(fls):
            car.prefer_left = True
        elif any([map.is_wall(x) for x in [fs, frs, fls]]):  # Obstacle is wall, so switch preferred direction
            car.prefer_left = True if car.rot > 0 else False
        car.reverse_count = 50
        car.steer_count = 50
        return
    if car.steer_count:  # Steer count means there was an obstacle and we reversed, so try turning
        if car.prefer_left:
            car.move(True, -1)
        else:
            car.move(True, 1)
        car.steer_count -= 1
    else:
        if not map.is_clear(rs):  # Obstacle on outer sensor but not emergency brake sensor
            car.move(True, -1)
        elif not map.is_clear(ls):
            car.move(True, 1)
        elif car.rot > 0.001:  # No obstacles? straighten up
            car.move(True, -1)
        elif car.rot < -0.001:
            car.move(True, 1)
        else:  # No obstacle, car already straight - full speed ahead
            car.move(True, 0)


def main(img, start_x, start_y):
    map = Map(img)
    margin = 50
    if start_x < 0 or start_y < 0:
        start_pos = complex(map.w / 2, map.h - margin)
    elif start_x < margin or start_y < margin or start_x > map.w - margin or start_y > map.h - margin:
        print("Start coordinates out of bounds - need to be at least {}px within the edge of the image. "
              "(x: [{}; {}], y: [{}; {}])".format(margin, margin, map.w - margin, margin, map.h - margin))
        exit(1)
    else:
        start_pos = complex(start_x, start_y)
    fig, ax = plt.subplots(1)
    ax.imshow(map.px)
    car = Car(start_pos)

    def plt_car_patch(c):
        corner = c.to_world(c.front_left)
        shapes = [
            plt.Circle((c.pos.real, c.pos.imag), radius=3, color='g'),
            plt.Rectangle((corner.real, corner.imag), c.width, c.length,
                      angle=math.degrees(car.rot), linewidth=2, edgecolor='g', facecolor='none')
        ]
        sensors = [c.to_world(s) for s in c.sensors]
        shapes += [plt.Circle((p.real, p.imag), radius=7, color='m' if map.is_clear(p) else 'c') for p in sensors]
        return [ax.add_patch(shape) for shape in shapes]

    def plt_init():
        return plt_car_patch(car)

    def plt_anim(_, c):
        update_car(map, c)
        global counter
        counter += 1
        if c.pos.imag <= 80:
            print(counter)
            time.sleep(2)
            exit()
        return plt_car_patch(c)

    _ = animation.FuncAnimation(fig, plt_anim, init_func=plt_init, fargs=(car,), interval=10, blit=True)
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Simulate obstacle avoiding car")
    parser.add_argument("file", type=str, nargs='?', help="Path to a PNG image of the map", default="maps/default_map.png")
    parser.add_argument("-x", type=int, help="X coordinate to start at", default=-1)
    parser.add_argument("-y", type=int, help="Y coordinate to start at", default=-1)
    args = parser.parse_args()
    main(args.file, args.x, args.y)
