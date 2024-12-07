from machine import I2C, Pin
from MPU1 import MPU6050
from wifi_connect import wifi_connect
from Multiplexer import Multiplexer
from CoinMotor import CoinVibrationMotor
import urequests
import time
import sys

# Function to fetch the current time from the server
def getTime():
    base_url = 'http://172.20.10.6:5000'
    try:
        response = urequests.get(f"{base_url}/time")
        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                datetimedata = data["message"]
                datetime_parts = datetimedata.split("/")
                date = datetime_parts[0]
                time = datetime_parts[1]
                formatted_time = f"{date}/{time}"
                print("Received time:", formatted_time)
            else:
                print("Unexpected data format: 'message' key not found")
                formatted_time = None
        else:
            print(f"Failed to fetch time. HTTP Status Code: {response.status_code}")
            formatted_time = None
        response.close()
    except Exception as e:
        print(f"Error fetching time: {e}")
        formatted_time = None
    return formatted_time

# Function to detect significant movement
def is_significant_movement(delta, threshold=3):
    return abs(delta) > threshold

# Function to determine bad posture based on movement
def is_bad_posture(current_value, initial_value, threshold=7.5):
    delta = current_value - initial_value
    return is_significant_movement(delta, threshold)

def main():
    base_url = 'http://172.20.10.6:5000'

    # Connect to Wi-Fi
    try:
        wifi_connect()
        print("Connected to Wi-Fi successfully!")
    except RuntimeError as e:
        print("Failed to connect to Wi-Fi:", e)
        sys.exit(0.1)

    # Initialize I2C and multiplexer
    i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
    mux = Multiplexer(i2c)
    channels = [0, 1, 2, 3, 4]

    # Initialize MPU6050 sensors
    mpu_sensors = {}
    for i, channel in enumerate(channels):
        mux.select_channel(channel)
        time.sleep(0.1)
        try:
            mpu_sensors[f'mpu{i+1}'] = MPU6050(i2c)
        except Exception as e:
            print(e)

    # Gather initial values for calibration
    initial_values = {}
    for i, channel in enumerate(channels):
        mux.select_channel(channel)
        time.sleep(0.1)
        gyro_x, gyro_y, gyro_z = mpu_sensors[f'mpu{i+1}'].get_gyroscope()

        # Convert to angles (degrees), assuming 0.1 sec between readings (adjust based on actual timing)
        angle_x = gyro_x * 1.1
        angle_y = gyro_y * 1.1
        angle_z = gyro_z * 1.1

        # Round the initial angles to the nearest tenth
        initial_values[f'mpu{i+1}'] = {
            "x": round(angle_x, 1),
            "y": round(angle_y, 1),
            "z": round(angle_z, 1)
        }

    # Map MPU sensors to body parts
    part_map = {
        "right_elbow": "mpu1",
        "left_elbow": "mpu2",
        "right_shoulder": "mpu3",
        "middle_back": "mpu4",
        "left_shoulder": "mpu5"
    }

    # Initialize the coin motor
    motor = CoinVibrationMotor(pin_number=26)

    while True:
        # Data structure for sensor readings
        sensor_data = {
            "right_shoulder": {"x": 0, "y": 0, "z": 0},
            "left_shoulder": {"x": 0, "y": 0, "z": 0},
            "middle_back": {"x": 0, "y": 0, "z": 0},
            "right_elbow": {"x": 0, "y": 0, "z": 0},
            "left_elbow": {"x": 0, "y": 0, "z": 0}
        }

        try:
            # Collect sensor data
            for part, mpu_key in part_map.items():
                channel = channels[int(mpu_key[-1]) - 1]
                mux.select_channel(channel)
                time.sleep(0.1)

                gyro_x, gyro_y, gyro_z = mpu_sensors[mpu_key].get_gyroscope()

                # Convert to angles (degrees), assuming 0.1 sec between readings
                angle_x = gyro_x * 1.1
                angle_y = gyro_y * 1.1
                angle_z = gyro_z * 1.1

                # Round the angles to the nearest tenth
                angle_x = round(angle_x, 1)
                angle_y = round(angle_y, 1)
                angle_z = round(angle_z, 1)

                # Subtract initial values to "zero" the sensor
                delta_x = angle_x - initial_values[mpu_key]["x"]
                delta_y = angle_y - initial_values[mpu_key]["y"]
                delta_z = angle_z - initial_values[mpu_key]["z"]

                # Only store significant movement
                if is_significant_movement(delta_x):
                    sensor_data[part]["x"] = delta_x
                if is_significant_movement(delta_y):
                    sensor_data[part]["y"] = delta_y
                if is_significant_movement(delta_z):
                    sensor_data[part]["z"] = delta_z

            # Check for bad posture
            posture_status = [{'left_shoulder': 0, 'middle_back': 0, 'right_shoulder': 0}]
            for part, mpu_key in {"right_shoulder": "mpu3", "middle_back": "mpu4", "left_shoulder": "mpu5"}.items():
                initial = initial_values[mpu_key]
                current = sensor_data[part]
                if (is_bad_posture(current["x"], initial["x"]) or
                    is_bad_posture(current["y"], initial["y"]) or
                    is_bad_posture(current["z"], initial["z"])):

                    posture_status[0][part] = 1
            print("Posture Status:", posture_status[0])

            # Activate the motor if bad posture is detected
            if any(status == 1 for status in posture_status[0].values()):
                motor.activate_for_duration(duration=1, duty_cycle=32768)

            # Get current date and time from the server
            current_datetime = getTime()

            if current_datetime:
                # Send data to the server with the date and time
                attempts = 3
                for attempt in range(attempts):
                    try:
                        response = urequests.post(f"{base_url}/store/real_data/{current_datetime}/", json=sensor_data)

                        if response.status_code == 202:
                            # Update calibration offsets with new initial values
                            calibration_offsets = {part: initial_values[mpu_key] for part, mpu_key in part_map.items()}
                            response_cal = urequests.post(f"{base_url}/caldata", json=calibration_offsets)
                            print(f"Calibration data sent: {response_cal.text}")
                            response_cal.close()

                            # Reset posture status
                            posture_status = [{'left_shoulder': 0, 'middle_back': 0, 'right_shoulder': 0}]
                            try:
                                posture_reset_response = urequests.post(f"{base_url}/postureER", json=posture_status)
                                print(f"Posture status reset: {posture_reset_response.text}")
                                posture_reset_response.close()
                            except Exception as e:
                                print(f"Error resetting posture status: {e}")

                            # Update initial_values with the newly calibrated values
                            for part, mpu_key in part_map.items():
                                channel = channels[int(mpu_key[-1]) - 1]
                                mux.select_channel(channel)
                                time.sleep(0.1)
                                gyro_x, gyro_y, gyro_z = mpu_sensors[mpu_key].get_gyroscope()

                                # Convert to angles (degrees), assuming 0.1 sec between readings
                                angle_x = gyro_x * 1.1
                                angle_y = gyro_y * 1.1
                                angle_z = gyro_z * 1.1

                                # Round the new angles
                                initial_values[mpu_key] = {
                                    "x": round(angle_x, 1),
                                    "y": round(angle_y, 1),
                                    "z": round(angle_z, 1)
                                }
                            print("Initial values updated after calibration:", initial_values)

                        response.close()

                        if any(status == 1 for status in posture_status[0].values()):
                            posture_response = urequests.post(f"{base_url}/postureER", json=posture_status)
                            print(f"Posture Status sent: {posture_response.text}")
                            posture_response.close()

                        break
                    except OSError as e:
                        print(f"Attempt {attempt+1} failed: {e}")
                        time.sleep(1)

            time.sleep(0.1)

        except Exception as e:
            print(e)

if __name__ == "__main__":
    main()
