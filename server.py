#!/usr/bin/python
import argparse
import socket
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
from urlparse import urlparse
from camera import Camera
from time import sleep  # Removed sleep from mjpeg do_GET loop


class CamHandler(BaseHTTPRequestHandler):
    def __init__(self, capture, *args):
        self.capture = capture
        self.content = open('index.html', 'r').read()
        BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(self):
        url = urlparse("http://{}:{}{}".format(self.client_address[0], self.client_address[1], self.path))
        if url.path.endswith('.mjpg'):
            while True:
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/jpeg')
                    self.end_headers()
                    self.wfile.write(self.capture.get_frame())
                    if url.query.startswith("dt="):
                        break
                except socket.error as ex:
                    print("Pipe closed: " + ex.args[1] if len(ex.args >= 2) else "")
                    break
                except KeyboardInterrupt:
                    break
            return
        elif self.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.content)
            return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", default="0.0.0.0", help="Server IP Address [Default 0.0.0.0]", dest="ip", type=str)
    parser.add_argument("-p", default=8080, help="Server Port [Default: 8080]", dest="port", type=int)
    parser.add_argument("-d", default="auto", help="Device Type [Default:auto] (pi|lepton|cv)", dest="device", type=str)
    results = parser.parse_args()

    ip = results.ip
    port = results.port
    device_type = results.device

    try:
        camera = Camera()
        Camera.initialize(camera, device_type)

        def handler(*args):
            CamHandler(camera, *args)

        server = ThreadedHTTPServer((ip, port), handler)

        print("Server Started on " + ip + ":" + str(port))
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()
    finally:
        camera.schedule_stop()


if __name__ == '__main__':
    main()
