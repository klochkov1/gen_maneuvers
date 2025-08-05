# This script generates maneuvers for an "intruder" we are working with.
# Flights at typical speed (base flight) always alternate with a maneuver (turn, altitude change, or acceleration).

# Script replaces the intruder block in the input params file. It can write the result to new file with suffix specified in the `result_file_suffix` variable.

import random
import sys

# result_file_suffix = ""
result_file_suffix = ".tmp"

# 20 maneuvers is approximately 10 minutes of simulated flight time for the object
# Increasing the number of maneuvers increases the initialization time of the simulation
num_maneuvers = 20

# Initial state of the intruder. 
x = random.choice([-1, 1]) * random.randint(1500, 5000)
y = random.choice([-1, 1]) * random.randint(1500, 5000)
# initial altitude
z = random.randint(500, 2000)
# heading azimuth
heading = random.randint(0, 360) 

# Base flight params
speed_min = 40 
speed_max = 65
basic_flight_duration_min = 10
basic_flight_duration_max = 30

# Altitude change config
altitude_min = 500
altitude_max = 3000
climb_delta_min = 100
climb_delta_max = 1000
climb_delta_step = 10
climb_rate_div_min = 10
climb_rate_div_max = 20

# Turn config
turn_angle_max = 90
turn_rate_min = 1  # degrees per second
turn_rate_max = 5

# Speed acceleration config
acceleration_min = 70
acceleration_max = 90
acceleration_duration_min = 5
acceleration_duration_max = 10

# Global vars
time = 5
current_altitude = z
maneuvers = []
current_speed = 0

def add_maneuver(state_block, duration):
    global time
    # Here we set the start time of the maneuver which is the end time of the previous maneuver
    maneuver_block = f"""
  maneuvers {{
    t: {time}
    state {{
      {state_block}
    }}
  }}
"""
    # Then we update the time so the next maneuver know when it starts and end this maneuver
    time += duration
    return maneuver_block

def basic_flight():
    speed = random.randrange(speed_min, speed_max + 1, 5)
    duration = random.randint(basic_flight_duration_min, basic_flight_duration_max)
    return add_maneuver(f"""horizontal_speed: {speed}
      climb_rate: 0
      turn_rate_dps: 0""", duration)

def turn():
    angle = random.randint(0, turn_angle_max)
    rate = random.randint(turn_rate_min, turn_rate_max)
    duration = int(round(abs(angle) / rate))
    return add_maneuver(f"turn_rate_dps: {random.choice([-1, 1]) * rate}", duration)

def change_altitude():
    global current_altitude
    delta = random.choice([-1, 1]) * random.randrange(climb_delta_min, climb_delta_max + 1, climb_delta_step)
    new_altitude = current_altitude + delta

    if new_altitude < altitude_min:
        delta = altitude_min - current_altitude
    elif new_altitude > altitude_max:
        delta = altitude_max - current_altitude

    rate = max(1, abs(delta) // random.randint(climb_rate_div_min, climb_rate_div_max))
    duration = abs(delta) // rate
    current_altitude += delta

    return add_maneuver(f"climb_rate: {rate if delta > 0 else -rate}", duration)

def accelerate():
    speed = random.randrange(acceleration_min, acceleration_max + 1, 5)
    duration = random.randint(acceleration_duration_min, acceleration_duration_max)
    return add_maneuver(f"horizontal_speed: {speed}", duration)

# Generate maneuvers sequence
for _ in range(num_maneuvers):
    # start with a basic flight
    maneuvers.append(basic_flight())

    # Randomly choose next maneuver
    maneuver_type = random.choice(["turn", "climb", "acceleration"])
    if maneuver_type == "turn":
        maneuvers.append(turn())
    elif maneuver_type == "climb":
        maneuvers.append(change_altitude())
    elif maneuver_type == "acceleration":
        maneuvers.append(accelerate())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please provide the input params.txt file to write intruder maneuvers there.")
        sys.exit(1)
    input_file = sys.argv[1]
    result_file = f"{input_file}{result_file_suffix}"

    with open(input_file, "r") as f:
        content = f.read()

    # Create new intruder block
    new_block = f"""
intruder {{
  initial_state {{
    position_ned {{
      x: {x}
      y: {y}
      z: {z}
    }}
    horizontal_speed: 60
    heading_deg: {heading}
  }}
""" + "".join(maneuvers) + "}"

    # Find the intruder block by brace counting and replace it
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
