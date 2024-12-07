import machine
import utime
import ustruct
import sys

class MPU6050:
    REG_PWR_MGMT_1 = 0x6B
    REG_ACCEL_XOUT_H = 0x3B
    REG_ACCEL_YOUT_H = 0x3D
    REG_ACCEL_ZOUT_H = 0x3F
    REG_GYRO_XOUT_H = 0x43
    REG_GYRO_YOUT_H = 0x45
    REG_GYRO_ZOUT_H = 0x47
    REG_WHO_AM_I = 0x75

    WHO_AM_I_EXPECTED = 0x68
    SENSITIVITY_ACCEL = 16384.0
    SENSITIVITY_GYRO = 131.0  # Sensitivity scale factor for gyroscope (degrees/sec)
    EARTH_GRAVITY = 9.80665

    def __init__(self, i2c, addr=0x68, filter_size=10):
        self.i2c = i2c
        self.addr = addr
        self.filter_size = filter_size

        # Buffers for filtering acceleration and gyroscope data
        self.acceleration_buffer = {"x": [], "y": [], "z": []}
        self.gyroscope_buffer = {"x": [], "y": [], "z": []}

        try:
            self._wake_up()
            self._check_connection()
        except Exception as e:
            print(f"Initialization error: {e}")
            sys.exit()

    def _reg_write(self, reg, data):
        """Write data to the specified register of the MPU6050."""
        try:
            msg = bytearray([data])
            self.i2c.writeto_mem(self.addr, reg, msg)
        except OSError as e:
            print(f"Error writing to register {reg}: {e}")
            sys.exit()

    def _reg_read(self, reg, nbytes=1):
        """Read data from the specified register of the MPU6050."""
        try:
            return self.i2c.readfrom_mem(self.addr, reg, nbytes)
        except OSError as e:
            print(f"Error reading from register {reg}: {e}")
            return None  # Return None on error

    def _wake_up(self):
        """Wake up the MPU6050 by writing to the power management register."""
        self._reg_write(self.REG_PWR_MGMT_1, 0)

    def _check_connection(self):
        """Check if the MPU6050 is connected and responding."""
        data = self._reg_read(self.REG_WHO_AM_I)
        if data != bytearray([self.WHO_AM_I_EXPECTED]):
            raise RuntimeError(f"Could not communicate with MPU6050 at address {self.addr}")

    def _read_sensor_data(self, reg, sensitivity):
        """Helper to read and convert raw sensor data."""
        data = self._reg_read(reg, 6)
        if data is None or len(data) < 6:
            print("Error: Incomplete data received from sensor.")
            return 0, 0, 0

        x = ustruct.unpack_from(">h", data, 0)[0]
        y = ustruct.unpack_from(">h", data, 2)[0]
        z = ustruct.unpack_from(">h", data, 4)[0]

        # Convert to meaningful units
        x = x / sensitivity
        y = y / sensitivity
        z = z / sensitivity

        return x, y, z

    def _apply_filter(self, buffer, value):
        """Apply a moving average filter to the given buffer."""
        buffer.append(value)
        if len(buffer) > self.filter_size:
            buffer.pop(0)
        return sum(buffer) / len(buffer)

    def get_acceleration(self):
        """Retrieve and filter accelerometer data from the MPU6050."""
        raw_x, raw_y, raw_z = self._read_sensor_data(self.REG_ACCEL_XOUT_H, self.SENSITIVITY_ACCEL)

        # Convert to m/s^2
        acc_x = raw_x * self.EARTH_GRAVITY
        acc_y = raw_y * self.EARTH_GRAVITY
        acc_z = raw_z * self.EARTH_GRAVITY

        # Filter the data
        filtered_x = self._apply_filter(self.acceleration_buffer["x"], acc_x)
        filtered_y = self._apply_filter(self.acceleration_buffer["y"], acc_y)
        filtered_z = self._apply_filter(self.acceleration_buffer["z"], acc_z)

        return filtered_x, filtered_y, filtered_z

    def get_gyroscope(self):
        """Retrieve and filter gyroscope data from the MPU6050."""
        raw_x, raw_y, raw_z = self._read_sensor_data(self.REG_GYRO_XOUT_H, self.SENSITIVITY_GYRO)

        # Filter the data
        filtered_x = self._apply_filter(self.gyroscope_buffer["x"], raw_x)
        filtered_y = self._apply_filter(self.gyroscope_buffer["y"], raw_y)
        filtered_z = self._apply_filter(self.gyroscope_buffer["z"], raw_z)

        return filtered_x, filtered_y, filtered_z
