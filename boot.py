import machine
from machine import Pin

buzzer = machine.PWM(machine.Pin(14), freq = 800, duty = 0)
buzzer.deinit()