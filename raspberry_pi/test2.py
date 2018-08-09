#!/usr/bin/python

import subprocess
import time


lut = {
'mute_state': ['KEY_MUTE'],
'enter': ['KEY_ENTER'],
'sleep_state': ['KEY_MENU', 'KEY_ENTER', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_DOWN', 'KEY_DOWN', 'KEY_ENTER', 'KEY_ENTER', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_UP', 'KEY_DOWN', 'KEY_ENTER', 'KEY_MENU']
}

def press_sequence_of_buttons(something_to_press):
    for button in lut[something_to_press]:
        press_button(button)

def press_button(button):
    p = subprocess.Popen('irsend SEND_ONCE vizio {}'.format(button))
    p.communicate()
    time.sleep(0.2)

