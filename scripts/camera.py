import io
from sys import modules
import threading
# from datetime import datetime
from time import sleep
import numpy as np

from util import default, raspberrypi, is_linux, thermal, lepton_in

if is_linux():
    import picamera

    try:
        from pylepton.Lepton3 import Lepton3
        import cv2
    except ImportError:
        pass
else:
    import cv2


class Camera(object):
    thread = None
    frame = None
    # last_access = datetime.now()
    device_type = ""
    width = 320
    height = 240
    size = height * width

    def initialize(self, device_type="auto", width=320, height=240):
        Camera.device_type = device_type
        if device_type == "auto":
            Camera.device_type = thermal() if lepton_in(modules) else raspberrypi() if is_linux() else default()

        self.width = width
        self.height = height

        if Camera.thread is None:
            Camera.thread = threading.Thread(target=self._thread)
            Camera.thread.stop_event = threading.Event()
            Camera.thread.start()

            # Return control to calling class when frame becomes available or when thread terminates
            print("Camera class initialised with device '{}'".format(Camera.device_type))
            while self.frame is None and self.thread is not None:
                sleep(0)
            print("Returning control to calling class")

            return self.thread is None
        else:
            print("Camera thread already initialised")
            return False

    def get_frame(self):
        # Camera.last_access = datetime.now()
        return self.frame

    def schedule_stop(self):
        if self.thread is not None:
            self.thread.stop_event.set()

    @staticmethod
    def should_stop(timeout=10):
        return Camera.thread.stop_event.is_set()  # or (datetime.now() - Camera.last_access).total_seconds() > timeout

    @classmethod
    def _thread(cls):
        if cls.device_type == raspberrypi():
            with picamera.PiCamera() as camera:
                # camera setup
                camera.resolution = (cls.width, cls.height)
                camera.hflip = True
                camera.vflip = True

                # let camera warm up
                camera.start_preview()
                sleep(2)

                stream = io.BytesIO()
                for _ in camera.capture_continuous(stream, 'jpeg', use_video_port=True):
                    stream.seek(0)
                    cls.frame = stream.read()
                    stream.seek(0)
                    stream.truncate()

                    if cls.should_stop():
                        break
        elif cls.device_type == thermal():
            while True:
                with Lepton3("/dev/spidev0.0") as l:
                    a, _ = l.capture()

                vflip = True
                if vflip:
                    cv2.flip(a, 0, a)

                cv2.normalize(a, a, 0, 65535, cv2.NORM_MINMAX)
                np.right_shift(a, 8, a)
                cls.frame = cv2.imencode('.jpg', np.uint8(a))[1].tobytes()

                if cls.should_stop():
                    break
        else:  # Default to default system camera device
            capture = cv2.VideoCapture(0)
            success, frame = capture.read()

            if success:
                cls.height, cls.width = frame.shape[:2]
                cls.size = cls.height * cls.width

                while success:
                    success, frame = capture.read()
                    cls.frame = cv2.imencode('.jpg', frame)[1].tobytes()

                    if cls.should_stop():
                        break
            else:
                print("Default camera device not found [{}]".format(cls.device_type))

        print("Setting thread to none")
        cls.thread = None
