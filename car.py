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

    def calibrate(self):
        logging.info("Calibrating car")
        calibration = {
            "straight": self._calibrate_speed(),
            "turning": self._calibrate_turning()
        }

        self._write_calibration(calibration)

    def _calibrate_speed(self):
        logging.debug("Calibrating speed")
        start_position = self.coordinates_provider.get_coordinates()
        self.left_motor.start(100, 5000)
        self.right_motor.start(100, 5000)
        end_position = self.coordinates_provider.get_coordinates()
        delta_position = start_position - end_position
        # TODO: complete

    def _calibrate_turning(self):
        logging.debug("Calibrating turning")
        # TODO: complete

    def _write_calibration(self, calibration):
        if os.path.exists(self.calibration_file):
            os.remove(self.calibration_file)
        with open(self.calibration_file, "w") as file:
            try:
                yaml.dump(calibration, file)
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

    def forward(self, distance):
        logging.info(f"Advancing {distance} meters forwards")
        power_left, power_right, movement_duration = self._calculate_straight_motors_power(distance)
        self.left_motor.forward(power_left)
        self.right_motor.forward(power_right)
        self.movement_timer.wait(movement_duration)
        logging.debug("Forward movement finished")

    def backward(self, distance):
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
        return self._calculate_motor_power(distance, meter_time, straight_calibration)

    def _calculate_turn_motor_power(self, angle):
        if not os.path.exists(self.calibration_file):
            raise RuntimeError(f"Calibration file not found in {self.calibration_file}")

        turn_calibration = self.calibration["turning"]
        degree_time = turn_calibration["duration"] / turn_calibration["angle"]
        power_left, power_right, movement_duration = self._calculate_motor_power(abs(angle), degree_time, turn_calibration)
        if angle > 0:
            return power_left, power_right, movement_duration
        elif angle < 0:
            return power_right, power_left, movement_duration
        else:
            return 0, 0, 0

    def _calculate_motor_power(self, distance, meter_time, calibration):
        movement_duration = meter_time * distance / 1000
        power_left = calibration["motorLeft"]
        power_right = calibration["motorRight"]
        self.left_motor.enable_device.frequency = calibration["frequency"]  # Hz
        self.right_motor.enable_device.frequency = calibration["frequency"]  # Hz
        logging.debug(
            f"Moving left motor at {power_left} and right motor at {power_right} with frequency {calibration['frequency']}Hz for {movement_duration}s")
        return power_left, power_right, movement_duration
