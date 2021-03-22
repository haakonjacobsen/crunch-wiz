import pandas as pd
import sys
import cv2
import os
from sys import platform
import argparse
from .handler import DataHandler  # noqa
import time

class MockAPI:
    """
    Mock api that reads from csv files instead of getting data from devices

    :type subscribers: list of (DataHandler, list of str)
    """
    f = open("crunch/skeleton/mock_data/test_data.csv", "r")
    skeleton_data = f.read()

    raw_data = ["body"]
    subscribers = {"body": []}

    def add_subscriber(self, data_handler, requested_data):
        """
        Adds a handler as a subscriber for a specific raw data

        :param data_handler: a data handler for a specific measurement that subscribes to a specific raw data
        :type data_handler: DataHandler
        :param requested_data: The specific raw data that the data handler subscribes to
        :type requested_data: list(str)
        """
        assert requested_data in self.subscribers.keys()
        self.subscribers[requested_data].append(data_handler)

    def connect(self):
        """ Simulates connecting to the device, starts reading from csv files and push data to handlers """
        for i in range(1000):
            self._mock_datapoint(i)

            # simulate delay of new data points by sleeping
            time.sleep(1)

    def _mock_datapoint(self, index):
        if index < len(self.skeleton_data):
            for subscriber in self.subscribers["body"]:
                subscriber.add_data_point(self.skeleton_data[index])


def display(datums):
    data = datums[0]
    cv2.imshow("OpenPose 1.7.0 - CrunchWiz", data.cvOutputData)
    key = cv2.waitKey(1)
    return key == 27


class RealAPI:
    """
    Mock api that reads from csv files instead of getting data from devices
    """
    raw_data = ["body"]
    subscribers = {"body": []}

    def add_subscriber(self, data_handler, requested_data):
        """
        Adds a handler as a subscriber for a specific raw data

        :param data_handler: a data handler for a specific measurement that subscribes to a specific raw data
        :type data_handler: DataHandler
        :param requested_data: The specific raw data that the data handler subscribes to
        :type requested_data: list(str)
        """
        assert requested_data in self.subscribers.keys()
        self.subscribers[requested_data].append(data_handler)

    def add_datapoint(self, datums):
        datum = datums[0]
        if datum.poseKeypoints is not None:
            fixed_data = [(row[0], row[1]) for row in datum.poseKeypoints[0]]
            for handler in self.subscribers["body"]:
                handler.add_data_point(fixed_data)

    def connect(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        try:
            if platform == "win32":
                # Change these variables to point to the correct folder (Release/x64 etc.)
                sys.path.append(dir_path + '/openpose/build/python/openpose/Release')
                y = dir_path + '/openpose/build/x64/Release;'
                z = dir_path + '/openpose/build/bin;'
                os.environ['PATH'] = os.environ['PATH'] + ';' + y + z
                import pyopenpose as op
            else:
                sys.path.append('/openpose/build/python')
                from openpose import pyopenpose as op
        except ImportError as e:
            print(
                'Error: OpenPose library could not be found. Did you enable `BUILD_PYTHON` in'
                ' CMake and have this Python script in the right folder?')
            raise e

        # Flags
        parser = argparse.ArgumentParser()
        parser.add_argument("--no-display", action="store_true", help="Disable display.")
        parser.add_argument("--frame_step", default=100)
        parser.add_argument("--fps_max", default=1)
        args = parser.parse_known_args()

        # Custom Params (refer to include/openpose/flags.hpp for more parameters)
        params = dict()
        params["model_folder"] = dir_path + "/openpose/models/"
        # Add others in path?
        for i in range(0, len(args[1])):
            curr_item = args[1][i]
            if i != len(args[1]) - 1:
                next_item = args[1][i + 1]
            else:
                next_item = "1"
            if "--" in curr_item and "--" in next_item:
                key = curr_item.replace('-', '')
                if key not in params:
                    params[key] = "1"
            elif "--" in curr_item and "--" not in next_item:
                key = curr_item.replace('-', '')
                if key not in params:
                    params[key] = next_item
        # Construct it from system arguments
        # op.init_argv(args[1])
        # oppython = op.OpenposePython()
        # Starting OpenPose
        opWrapper = op.WrapperPython(op.ThreadManagerMode.AsynchronousOut)
        opWrapper.configure(params)
        opWrapper.start()
        print("OpenPose Process successfully started, press ESC to exit")

        user_wants_to_exit = False
        while not user_wants_to_exit:
            dataframe = op.VectorDatum()
            if opWrapper.waitAndPop(dataframe):
                if not args[0].no_display:
                    user_wants_to_exit = display(dataframe)
                self.add_datapoint(dataframe)
            else:
                break
        print("OpenPose Exited")