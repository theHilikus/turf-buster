import argparse
import logging
import os
import signal
import sys

from car import Car


def main() -> int:
    args = parse_arguments()
    configure_logger(args)
    the_car = Car(args)

    def stop_everything(sig, frame):
        logging.info("Stopping everything")
        the_car.stop()

    signal.signal(signal.SIGINT, stop_everything)
    signal.signal(signal.SIGTERM, stop_everything)
    if args.command.startswith("st"):
        the_car.stop()
    elif args.command.startswith("fo"):
        the_car.forward(args.distance)
    elif args.command.startswith("ba"):
        the_car.backward(args.distance)
    elif args.command.startswith("ca"):
        the_car.calibrate()
    else:
        raise RuntimeError(f"Unknown command: {args.command}")

    return 0


def parse_arguments():
    parser = argparse.ArgumentParser(description="Starts turf-buster")
    parser.add_argument("--working-folder", help="Location to store operational files", default="/opt/turf-buster/",
                        type=dir_path)
    parser.add_argument("--fake-locations", help="A list of fake locations. Disables getting locations from the GPS")
    parser.add_argument("-v", "--verbose", help="increase log verbosity", action="store_true")
    # parser.add_argument("command", help="The command to execute", choices=['calibrate', "move", "turn", "stop"])
    subparsers = parser.add_subparsers(help="Commands help", dest="command", required=True)

    parser_move = subparsers.add_parser("forward", help="Moves the car forward the specified distance in meters")
    parser_move.add_argument("distance", type=float, help="The distance to move in meters")

    parser_move = subparsers.add_parser("backward", help="Moves the car backward the specified distance in meters")
    parser_move.add_argument("distance", type=float, help="The distance to move in meters")

    parser_turn = subparsers.add_parser("turn", help="Turns the car for the specified angle")
    parser_turn.add_argument("angle", type=int, help="The angle to turn in degrees")

    subparsers.add_parser("stop", help="Stops all motors")

    args = parser.parse_args()
    return args


def dir_path(folder):
    if os.path.isdir(folder):
        if not folder.endswith("/"):
            folder = folder + "/"
        return folder
    else:
        raise NotADirectoryError(folder)


def configure_logger(args):
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logger_format = '%(asctime)s.%(msecs)03d %(levelname)-5s -- %(name)-8s : %(message)s'
    logging.basicConfig(format=logger_format, level=log_level, stream=sys.stdout, datefmt="%H:%M:%S")


if __name__ == '__main__':
    sys.exit(main())
