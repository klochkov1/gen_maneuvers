# This script generates maneuvers for an "intruder" we are working with.
# Flights at typical speed (base flight) always alternate with a maneuver (turn, altitude change, or acceleration).
# Base flights and maneuvers have random duration and other parameters, but values are limitied byt the parameters below.

# Script replaces the intruder block in the input params file. It can write the result to new file with suffix specified in the `result_file_suffix` variable.

import random
import re
import sys

# result_file_suffix = ""
result_file_suffix = ".tmp"

# 20 maneuvers is approximately 10 minutes of simulated flight time for the object
# Increasing the number of maneuvers increases the initialization time of the simulation
num_maneuvers = 20

# Initial state of the intruder relative to the strating point 
x = random.choice([-1, 1]) * random.randint(2000, 5000)
y = random.choice([-1, 1]) * random.randint(2000, 5000)
# heading azimuth
heading = random.randint(0, 360) 

# Base flight params
speed_min = 38
speed_max = 62
# basic_flight_duration_min = 10
basic_flight_duration_min = 5
basic_flight_duration_max = 20

# Altitude change config
altitude_min = 600
altitude_max = 3000
climb_delta_min = 100
climb_delta_max = 1000
climb_delta_step = 10
climb_rate_min_climb = 5
climb_rate_max_climb = 10
climb_rate_min_descent = 5
climb_rate_max_descent = 20
speed_change_climb = 5  # Static speed reduction during climb (m/s)

# Turn config
turn_angle_min = 10
turn_angle_max = 100
turn_rate_min = 3  
turn_rate_max = 15

# Speed acceleration config
acceleration_min = 70
acceleration_max = 90
acceleration_duration_min = 5
acceleration_duration_max = 10

# Global vars
time = 5
current_speed = 50  # Initial cruise speed
maneuvers = []
current_altitude = None 

def add_maneuver(state_block, duration):
    global time
    if duration < 1:
        duration = 1
    maneuver_block = f"""
  maneuvers {{
    t: {time}
    state {{
      {state_block}
    }}
  }}
"""
    time += duration
    return maneuver_block

def basic_flight():
    speed = random.randint(speed_min, speed_max + 1)
    global current_speed
    current_speed = speed
    duration = random.randint(basic_flight_duration_min, basic_flight_duration_max)
    return add_maneuver(f"""horizontal_speed: {speed}
      climb_rate: 0
      turn_rate_dps: 0""", duration)

def turn():
    angle = random.randint(turn_angle_min, turn_angle_max + 1)
    rate = random.randint(turn_rate_min, turn_rate_max)
    duration = max(1, int(round(angle / rate)))
    return add_maneuver(f"turn_rate_dps: {random.choice([-1, 1]) * rate}", duration)

def change_altitude():
    global current_altitude, current_speed
    delta = random.choice([-1, 1]) * random.randrange(climb_delta_min, climb_delta_max + 1, climb_delta_step)
    new_altitude = current_altitude + delta

    if new_altitude < altitude_min:
        delta = altitude_min - current_altitude
    elif new_altitude > altitude_max:
        delta = altitude_max - current_altitude

    if delta > 0:
        rate = random.randint(climb_rate_min_climb, climb_rate_max_climb)
        adjusted_speed = max(speed_min, current_speed - speed_change_climb)
    else:
        rate = random.randint(climb_rate_min_descent, climb_rate_max_descent)
        adjusted_speed = min(speed_max, current_speed + speed_change_climb)

    duration = max(1, abs(delta) // rate)
    current_altitude += delta
    current_speed = adjusted_speed

    climb_rate_value = rate if delta > 0 else -rate
    return add_maneuver(f"""horizontal_speed: {adjusted_speed}
      climb_rate: {climb_rate_value}""", duration)

def accelerate():
    speed = random.randint(acceleration_min, acceleration_max)
    duration = random.randint(acceleration_duration_min, acceleration_duration_max)
    
    global current_speed
    current_speed = speed
    
    return add_maneuver(f"horizontal_speed: {speed}", duration)

def land():
    global current_altitude, current_speed
    if current_altitude > 0:
        rate = 150
        delta = -current_altitude
        duration = max(1, abs(delta) // rate)
        current_altitude = 0
        current_speed = 90
        first = add_maneuver(f"""horizontal_speed: 90
      climb_rate: {-rate}""", duration)
        current_speed = 0
        second = add_maneuver(f"""horizontal_speed: 0
      climb_rate: 0""", 1)
        return first + second
    else:
        current_speed = 0
        return add_maneuver(f"""horizontal_speed: 0
      climb_rate: 0""", 1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please provide the input params.txt file to write intruder maneuvers there.")
        sys.exit(1)
    input_file = sys.argv[1]
    result_file = f"{input_file}{result_file_suffix}"

    with open(input_file, "r") as f:
        content = f.read()

    m = re.search(r'^\s*altitude:\s*([+-]?\d+)\s*$', content, flags=re.MULTILINE)
    h_ref_asl = int(m.group(1)) if m else 200

    initial_offset = random.randint(400, 2000)
    current_altitude = h_ref_asl + initial_offset
    initial_z = h_ref_asl - current_altitude

    landing_time = random.randint(270, 420)
    while time < landing_time:
        maneuvers.append(basic_flight())
        maneuver_type = random.choices(["turn", "climb", "acceleration"], weights=[50, 35, 15])[0]
        if maneuver_type == "turn":
            maneuvers.append(turn())
        elif maneuver_type == "climb":
            maneuvers.append(change_altitude())
        elif maneuver_type == "acceleration":
            maneuvers.append(accelerate())

    maneuvers.append(land())

    new_block = f"""
intruder {{
  initial_state {{
    position_ned {{
      x: {x}
      y: {y}
      z: {initial_z}
    }}
    horizontal_speed: 55
    heading_deg: {heading}
  }}
""" + "".join(maneuvers) + "}"

    start = content.find('intruder {')
    if start != -1:
        depth = 0
        end = None
        for i in range(start, len(content)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end:
            content = content[:start] + new_block + content[end:]
    else:
        content += "\n" + new_block

    with open(result_file, "w") as f:
        f.write(content)
    
    print(f"{result_file}")
