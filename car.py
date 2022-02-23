import logging
import os
from threading import Event

import yaml
from gpiozero import Button
from gpiozero import PhaseEnableMotor

from location.provider import CoordinatesProvider


class Car:
    def __init__(self, args):
        self.calibration_file = args.working_folder + "locomotion-calibration.yml"
        if os.path.exists(self.calibration_file):
            self.calibration = self._read_calibration()
        self.coordinates_provider = CoordinatesProvider()
        self.left_motor = PhaseEnableMotor(phase=17, enable=27)
        self.right_motor = PhaseEnableMotor(phase=6, enable=5)
        self.stop_button = Button(20)
        self.stop_button.when_pressed = self.stop
        self.movement_timer = Event()

    def _read_calibration(self):
        with open(self.calibration_file, "r") as file:
            try:
                return yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(exc)
                return None

    def calibrate(self, args):
        logging.info("Calibrating car")
        calibration = {
            "straight": self._calibrate_speed(args.straight_power, args.frequency, args.duration),
            "turning": self._calibrate_turning(args.turn_power_left, args.turn_power_right, args.frequency, args.duration)
        }

        self._write_calibration(calibration)

    def _calibrate_speed(self, straight_power, frequency, duration):
        power_left = straight_power
        power_right = straight_power
        logging.debug(f"Calibrating speed with power_left = {power_left} and power_right = {power_right} for a duration of {duration}ms. PWM frequency = {frequency}Hz")
        self.left_motor.enable_device.frequency = frequency
        self.left_motor.forward(power_left)
        self.right_motor.enable_device.frequency = frequency
        self.right_motor.forward(power_right)
        distance = input("What was the distance travelled in meters? ")
        result = {
            "motorLeft": float(power_left),
            "motorRight": float(power_right),
            "frequency": int(frequency),
            "duration": int(duration),
            "distance": float(distance)
        }

        return result

    def _calibrate_turning(self, turn_power_left, turn_power_right, frequency, duration):
        power_left = turn_power_left
        power_right = turn_power_right
        logging.debug(f"Calibrating turning with power_left = {power_left} and power_right = {power_right} for a duration of {duration}ms. PWM frequency = {frequency}Hz")
        self.left_motor.enable_device.frequency = frequency
        self.left_motor.forward(power_left)
        self.right_motor.enable_device.frequency = frequency
        self.right_motor.forward(power_right)
        angle = input("What was the rotation in degrees? ")
        result = {
            "motorLeft": float(power_left),
            "motorRight": float(power_right),
            "frequency": int(frequency),
            "duration": int(duration),
            "angle": int(angle)
        }

        return result

    def _write_calibration(self, calibration):
        if os.path.exists(self.calibration_file):
            os.remove(self.calibration_file)
        with open(self.calibration_file, "w") as file:
            try:
                yaml.dump(calibration, file)
                logging.info(f"Calibration file wrote to {self.calibration_file}")
            except yaml.YAMLError as exc:
                print(exc)

    def stop(self):
        logging.info("Stopping car")
        self.left_motor.stop()
        self.right_motor.stop()
        self.movement_timer.set()  # interrupt threads sleeping

    def turn(self, degrees):
        logging.info(f"Turning {degrees} degrees")
        power_left, power_right, movement_duration = self._calculate_turn_motor_power(degrees)
        self.left_motor.forward(power_left)
        self.right_motor.forward(power_right)
        self.movement_timer.wait(movement_duration)
        logging.debug("Turning movement finished")

    def move(self, distance):
        if distance > 0:
            self._forward(distance)
        elif distance < 0:
            self._backward(abs(distance))

    def _forward(self, distance):
        logging.info(f"Advancing {distance} meters forwards")
        power_left, power_right, movement_duration = self._calculate_straight_motors_power(distance)
        self.left_motor.forward(power_left)
        self.right_motor.forward(power_right)
        self.movement_timer.wait(movement_duration)
        logging.debug("Forward movement finished")

    def _backward(self, distance):
        logging.info(f"Advancing {distance} meters backward")
        power_left, power_right, movement_duration = self._calculate_straight_motors_power(distance)
        self.left_motor.backward(power_left)
        self.right_motor.backward(power_right)
        self.movement_timer.wait(movement_duration)
        logging.debug("Backward movement finished")

    def _calculate_straight_motors_power(self, distance):
        if not os.path.exists(self.calibration_file):
            raise RuntimeError(f"Calibration file not found in {self.calibration_file}")

        straight_calibration = self.calibration["straight"]
        meter_time = straight_calibration["duration"] / straight_calibration["distance"]
        power_left, power_right, movement_duration = self._calculate_motor_power(distance, meter_time, straight_calibration)
        logging.debug(f"Moving left motor at {power_left} and right motor at {power_right} with frequency {straight_calibration['frequency']}Hz for {movement_duration}s")
        return power_left, power_right, movement_duration

    def _calculate_turn_motor_power(self, angle):
        if not os.path.exists(self.calibration_file):
            raise RuntimeError(f"Calibration file not found in {self.calibration_file}")

        turn_calibration = self.calibration["turning"]
        degree_time = turn_calibration["duration"] / turn_calibration["angle"]
        if angle > 0:
            power_left, power_right, movement_duration = self._calculate_motor_power(abs(angle), degree_time, turn_calibration)
        elif angle < 0:
            power_right, power_left, movement_duration = self._calculate_motor_power(abs(angle), degree_time, turn_calibration)
        else:
            power_left, power_right, movement_duration = 0, 0, 0

        logging.debug(f"Moving left motor at {power_left} and right motor at {power_right} with frequency {turn_calibration['frequency']}Hz for {movement_duration}s")

        return power_left, power_right, movement_duration

    def _calculate_motor_power(self, distance, meter_time, calibration):
        movement_duration = meter_time * distance / 1000
        power_left = calibration["motorLeft"]
        power_right = calibration["motorRight"]
        self.left_motor.enable_device.frequency = calibration["frequency"]  # Hz
        self.right_motor.enable_device.frequency = calibration["frequency"]  # Hz

        return power_left, power_right, movement_duration
