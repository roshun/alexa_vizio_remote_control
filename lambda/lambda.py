from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import os
import time

myAWSIoTMQTTClient = AWSIoTMQTTClient("Vizio TV Remote")


class Intent:
    def __init__(self, intent_type, intent_value, volume_amount=1):
        self.intent_type = intent_type
        self.intent_value = intent_value
        self.volume_amount = volume_amount
        self.card_title, self.speech_output, self.pi_command = self.build_response()
        self.should_end_session = True

    def build_response(self):
        card_title = ''
        speech_output = ''
        pi_command = ''
        if self.intent_type == 'button':
            card_title = 'Vizio TV Remote press {}'.format(self.intent_value)
            speech_output = 'Pressing {} on your Vizio TV'.format(self.intent_value)
            pi_command = '{} {}'.format(self.intent_type, self.intent_value)
        elif self.intent_type == 'power_state':
            card_title = 'Vizio TV Remote turn {}'.format(self.intent_value)
            speech_output = 'Turning {} your Vizio TV'.format(self.intent_value)
            pi_command = '{} {}'.format(self.intent_type, self.intent_value)
        elif self.intent_type == 'volume_direction':
            card_title = 'Vizio TV Remote turning volume {} by {}'.format(self.intent_value, self.volume_amount)
            speech_output = 'Turning the volume {} by {} on your Vizio TV'.format(self.intent_value, self.volume_amount)
            pi_command = 'volume {} {}'.format(self.intent_value, self.volume_amount)
        elif self.intent_type == 'search':
            card_title = 'Vizio TV Remote search for {}'.format(self.intent_value)
            speech_output = 'Searching for {} on your Vizio TV'.format(self.intent_value)
            pi_command = '{} {}'.format(self.intent_type, self.intent_value)
        elif self.intent_type == "video_service":
            card_title = 'Vizio TV Remote opening video service {}'.format(self.intent_value)
            speech_output = 'Opening the {} app on your Vizio TV'.format(self.intent_value)
            pi_command = '{} {}'.format(self.intent_type, self.intent_value)
        elif self.intent_type == 'clear':
            card_title = "Vizio TV remote: clearing the search bar"
            speech_output = "Clearing the search bar on your Vizio TV"
            pi_command = '{}'.format(self.intent_type)
        else:
            get_error_response()
        return card_title, speech_output, pi_command


def lambda_handler(event, context):
    mqtt_setup(myAWSIoTMQTTClient)

    if (event["session"]["application"]["applicationId"] !=
            "amzn1.ask.skill.197427b8-71b0-45bb-a9ce-ff4488db467d"):
        raise ValueError("Invalid Application ID")

    #    if event["session"]["new"]:
    #        on_session_started({"requestId": event["request"]["requestId"]}, event["session"])

    if event["request"]["type"] == "LaunchRequest":
        # return on_launch(event["request"], event["session"])
        return on_launch()
    elif event["request"]["type"] == "IntentRequest":
        # return on_intent(event["request"], event["session"])
        return on_intent(event['request'])
    # elif event["request"]["type"] == "SessionEndedRequest":
    #     return on_session_ended(event["request"], event["session"])


def mqtt_setup(client):
    # MQTT Parameters
    host = "a2f1bum09vr1fe.iot.us-east-1.amazonaws.com"
    root_ca_path = os.path.join('certificates', 'root-CA.crt')
    private_key_path = os.path.join('certificates', 'RaspberryPi.private.key')
    certificate_path = os.path.join('certificates', 'RaspberryPi.cert.pem')

    client.configureEndpoint(host, 8883)
    client.configureCredentials(root_ca_path, private_key_path, certificate_path)

    # AWSIoTMQTTClient connection configuration
    client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    client.configureDrainingFrequency(2)  # Draining: 2 Hz
    client.configureConnectDisconnectTimeout(10)  # 10 sec
    client.configureMQTTOperationTimeout(5)  # 5 sec


# def on_session_started(session_started_request, session):
#     print "Starting new session."

def on_launch():
    return get_welcome_response()


def on_intent(intent_request):
    if intent_request["intent"]["name"] == "Vizio":
        # Now, let's figure out which intent type was selected
        supported_intent_slots = ['power_state', 'video_service', 'button', 'search', 'volume_direction']

        for i in supported_intent_slots:
            if 'value' in intent_request['intent']['slots'][i]:
                if 'value' in intent_request['intent']['slots']['volume_amount']:
                    intent = Intent(intent_type=i, intent_value=intent_request['intent']['slots'][i]['value'],
                                    volume_amount=intent_request['intent']['slots']['volume_amount']['value'])
                else:
                    intent = Intent(intent_type=i, intent_value=intent_request['intent']['slots'][i]['value'])
    elif intent_request["intent"]["name"] == "clear":
        intent = Intent(intent_type='clear', intent_value=None)
    else:
        return get_error_response()

    if not publish_to_pi(intent.pi_command):
        return get_no_acknowledgement_response(pi_command=intent.pi_command)

    return build_response({}, build_speechlet_response(title=intent.card_title, output=intent.speech_output,
                                                       pi_command=intent.pi_command,
                                                       reprompt_text=None,
                                                       should_end_session=intent.should_end_session))


def get_welcome_response():
    session_attributes = {}
    card_title = "TV Remote"
    speech_output = "Welcome to the Alexa TV remote skill. " \
                    "You can ask me to do various things to control your tv. " \
                    "Try asking me to turn on or off, press a button, turn up or " \
                    "down the volume, or search for something."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(title=card_title, output=speech_output,
                                                                       reprompt_text=None,
                                                                       should_end_session=should_end_session))


def get_no_acknowledgement_response(pi_command):
    session_attributes = {}
    card_title = "ERROR: TV Remote did not respond!"
    speech_output = "Error. Remote did not respond to your request. Please ask for help to get a list of " \
                    "commands you can try"
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(title=card_title, output=speech_output,
                                                                       reprompt_text=None,
                                                                       should_end_session=should_end_session,
                                                                       pi_command=pi_command))


def get_error_response():
    session_attributes = {}
    card_title = "ERROR: Invalid command to TV Remote"
    speech_output = "Error. Invalid request to TV Remote. Please ask for help to get a list of commands you can try"
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(title=card_title, output=speech_output,
                                                                       reprompt_text=None,
                                                                       should_end_session=should_end_session))


def build_speechlet_response(title, output, reprompt_text, should_end_session, pi_command=''):
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output,
            "pi_command": pi_command
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }


def publish_to_pi(string):
    topic = 'remote'
    timeout = 2

    class CallbackWrapper:
        def __init__(self):
            self.response_received = False

        def callback(self, client, userdata, message):
            if 'Acknowledged' in message.payload:
                self.response_received = True

    myAWSIoTMQTTClient.connect()

    # Publish to main topic
    c = CallbackWrapper()
    myAWSIoTMQTTClient.publish('$aws/things/RaspberryPi/{}'.format(topic), string, 1)

    # Subscribe to response topic
    myAWSIoTMQTTClient.subscribe('$aws/things/RaspberryPi/{}/response'.format(topic), 1, c.callback)

    # Wait for a valid response or timeout
    current_time = time.time()
    while not (c.response_received or time.time() - current_time > timeout):
        time.sleep(0.1)

    myAWSIoTMQTTClient.unsubscribe('$aws/things/RaspberryPi/{}/response'.format(topic))
    myAWSIoTMQTTClient.disconnect()
    return c.response_received
