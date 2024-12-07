from machine import Pin, PWM
import utime

class CoinVibrationMotor:
    def __init__(self, pin_number=26):
        self.motor_pin = PWM(Pin(pin_number))
        self.motor_pin.freq(500)  # Set frequency for PWM
        self.duty_cycle = 0        # Initialize duty cycle
        self.is_active = False      # Track motor state

    def turn_on(self, duty_cycle=32768):  # Duty cycle from 0 (off) to 65535 (full speed)
        if not self.is_active:
            print("Turning motor ON...")
            self.motor_pin.duty_u16(duty_cycle)  # Set the PWM duty cycle
            self.is_active = True
            print("Motor is ON with duty cycle:")

    def turn_off(self):
        if self.is_active:
            print("Turning motor OFF...")
            self.motor_pin.duty_u16(0)  # Turn off the motor
            self.is_active = False
            print("Motor is OFF")

    def activate_for_duration(self, duration=1, duty_cycle=32768):
        print(f"Activating motor for {duration} seconds at duty cycle {duty_cycle}...")
        self.turn_on(duty_cycle)  # Turn on motor with specified duty cycle
        utime.sleep(duration)      # Keep it on for the specified duration
        self.turn_off()            # Turn off motor

