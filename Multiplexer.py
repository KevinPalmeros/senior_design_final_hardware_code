class Multiplexer:
    def __init__(self, i2c, address=0x70):
        self.i2c = i2c
        self.address = address

    def select_channel(self, channel):
        if channel < 0 or channel > 7:
            raise ValueError("Multiplexer channel must be between 0 and 7")
        try:
            self.i2c.writeto(self.address, bytearray([1 << channel]))
        except OSError as e:
            print(f"Error selecting channel {channel} on multiplexer: {e}")