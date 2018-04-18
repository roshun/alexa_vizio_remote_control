from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import subprocess
from time import gmtime, localtime, strftime

import argparse


class VizioRemoteControl:
    def __init__(self, endpoint, root_cert, cert, key, web_socket=False):
        self.endpoint = endpoint
        self.root_cert = root_cert
        self.cert = cert
        self.key = key
        self.web_socket = web_socket

        # Parameters
        self.QoS = 1
        self.topic = 'remote'

        # Set up logging
        self.configure_logging(verbosity=logging.INFO)

        # Init AWSIoTMQTTClient
        if self.web_socket:
            self.client = AWSIoTMQTTClient("basicSub", useWebsocket=True)
            self.client.configureEndpoint(self.endpoint, 443)
            self.client.configureCredentials(self.root_cert)
        else:
            self.client = AWSIoTMQTTClient("basicSub")
            self.client.configureEndpoint(self.endpoint, 8883)
            self.client.configureCredentials(self.root_cert, self.key, self.cert)

        # AWSIoTMQTTClient connection configuration
        self.client.configureAutoReconnectBackoffTime(1, 32, 20)
        self.client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        self.client.configureDrainingFrequency(2)  # Draining: 2 Hz
        self.client.configureConnectDisconnectTimeout(10)  # 10 sec
        self.client.configureMQTTOperationTimeout(5)  # 5 sec

        # Connect and subscribe to AWS IoT
        self.client.connect()
        self.client.subscribe(topic='$aws/things/RaspberryPi/{}'.format(self.topic),
                              QoS=self.QoS, callback=self.callback)

    @staticmethod
    def wait_forever():
        while True:
            time.sleep(1)

    @staticmethod
    def vizio_search(message):
        # Navigate to the Netflix search screen
        # TODO: handle searching after a previous search versus searching from scratch, maybe use a different keyword?

        subprocess.Popen("irsend SEND_ONCE vizio KEY_NETFLIX", shell=True)
        time.sleep(3)
        subprocess.Popen("irsend SEND_ONCE vizio KEY_OK", shell=True)
        time.sleep(1)
        for i in list(message):
            if i == " ":
                subprocess.Popen("irsend SEND_ONCE vizio KEY_SPACE", shell=True)
            else:
                subprocess.Popen("irsend SEND_ONCE vizio KEY_" + i.upper(), shell=True)
            time.sleep(1)
        subprocess.Popen("irsend SEND_ONCE vizio KEY_SPACE", shell=True)
        time.sleep(1)
        subprocess.Popen("irsend SEND_ONCE vizio KEY_DELETE", shell=True)
        time.sleep(1)
        subprocess.Popen("irsend SEND_ONCE vizio KEY_RIGHT", shell=True)
        time.sleep(1)
        subprocess.Popen("irsend SEND_ONCE vizio KEY_OK", shell=True)
        time.sleep(1)
        subprocess.Popen("irsend SEND_ONCE vizio KEY_OK", shell=True)
        return True

    @staticmethod
    def vizio_clear():
        subprocess.Popen("irsend SEND_START vizio KEY_LEFT", shell=True)
        time.sleep(2)
        subprocess.Popen("irsend SEND_STOP vizio KEY_LEFT", shell=True)
        time.sleep(0.5)
        subprocess.Popen("irsend SEND_START vizio KEY_DELETE", shell=True)
        time.sleep(5)
        subprocess.Popen("irsend SEND_STOP vizio KEY_DELETE", shell=True)
        return True

    @staticmethod
    def vizio_open_video_service(service):
        subprocess.Popen("irsend SEND_ONCE vizio KEY_" + service, shell=True)
        time.sleep(3)
        return True

    # Custom MQTT message callback
    def callback(self, client, userdata, message):
        repetition = 1
        if message.payload.split()[0] == "search":
            self.vizio_search(message.payload.replace("search ", ""))
            self.respond()
            return
        elif message.payload.split()[0] == "clear":
            self.vizio_clear()
            self.respond()
            return
        elif message.payload.split()[0] == "video_service":
            self.vizio_open_video_service(message.payload.upper().split()[1])
            self.respond()
            return
        else:
            button = ''
            if message.payload.upper().split()[1] == "OKAY":
                button = "KEY_OK"
            elif (message.payload.upper().split()[1] == "ON" or message.payload.upper().split()[1] == "OFF") \
                    and message.payload.split()[0] == "power_state":
                button = "KEY_POWER"
            elif message.payload.split()[0] == "volume":
                if message.payload.upper().split()[1] == "UP":
                    button = "KEY_VOLUMEUP"
                    repetition = int(message.payload.split()[2])
                    # print "Turning volume up by %s" % repetition
                elif message.payload.upper().split()[1] == "DOWN":
                    button = "KEY_VOLUMEDOWN"
                    repetition = int(message.payload.split()[2])
                    # print "Turning volume down by %s" % repetition
                # TODO: build in some error handling here for incorrect volume settings
            else:
                button = "KEY_" + message.payload.upper().split()[1]
            for i in range(repetition):
                subprocess.Popen("irsend SEND_ONCE vizio " + button, shell=True)
                time.sleep(0.3)

        with open("/home/pi/alexa_remote_commands_vizio.log", "a") as command_logger:
            command_logger.write(strftime("%Y-%m-%d %H:%M:%S", localtime()) +
                                 "\t" + message.topic + "\t" + message.payload + "\n")

    def respond(self):
        string = 'Acknowledged'
        self.client.publishAsync('$aws/things/RaspberryPi/{}/response'.format(self.topic), string, 1, None)

    @staticmethod
    def configure_logging(verbosity):
        # Configure logging
        logger = logging.getLogger("AWSIoTPythonSDK.core")
        logger.setLevel(verbosity)
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)


def parse_args():
    # Usage
    usage = """
    Use certificate based mutual authentication:
    python vizio_remote_control.py -e <endpoint> -r <rootCAFilePath> -c <certFilePath> -k <privateKeyFilePath>

    Use MQTT over WebSocket:
    python vizio_remote_control.py -e <endpoint> -r <rootCAFilePath> -w

    Type "python vizio_remote_control.py -h" for available options.
    """
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument('-e', '--endpoint', required=True, help='Your AWS IoT custom endpoint')
    parser.add_argument('-r', '--rootCA', required=True, help='Root CA file path')
    parser.add_argument('-c', '--cert', required=False, help='Certificate file path')
    parser.add_argument('-k', '--key', required=False, help='Private key file path')
    parser.add_argument('-w', '--web_socket', default=False, help='Use MQTT over WebSocket')
    args = parser.parse_args()

    # Some logic
    if not args.web_socket:
        if not args.cert:
            parser.error("Missing '-c' or '--cert'")
        if not args.key:
            parser.error("Missing '-k' or '--key'")

    return args


def main():
    args = parse_args()
    remote = VizioRemoteControl(endpoint=args.endpoint, root_cert=args.rootCA, cert=args.cert,
                                key=args.key, web_socket=args.web_socket)
    remote.wait_forever()


if __name__ == '__main__':
    main()
