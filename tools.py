# ================================
# Imports
# ================================
import requests
import json
from datetime import datetime
import psutil
import threading
import dateparser
import time
from playsound import playsound
import pywhatkit as kit
import urllib.parse
import pyautogui
import os
import subprocess
import shutil
import platform
import re
from comtypes import CLSCTX_ALL
import screen_brightness_control as sbc  # For brightness control

# For volume control
from ctypes import cast, POINTER
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pygame

# ================================
# TOOLS SECTION
# ================================
def system_check():
    info = {
        "System": platform.system(),
        "Node Name": platform.node(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Architecture": platform.architecture()[0],
        "CPU Cores": psutil.cpu_count(logical=False),
        "Logical Processors": psutil.cpu_count(logical=True),
        "RAM Size (GB)": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "Disk Space": {
            "Total (GB)": round(shutil.disk_usage('/').total / (1024 ** 3), 2),
            "Used (GB)": round(shutil.disk_usage('/').used / (1024 ** 3), 2),
            "Free (GB)": round(shutil.disk_usage('/').free / (1024 ** 3), 2)
        },
        "Battery Status": get_battery_info()
    }
    return json.dumps(info, indent=4)

def get_battery_info():
    battery = psutil.sensors_battery()
    if battery is None:
        return "Battery information not available"
    return f"{battery.percent}% ({'Charging' if battery.power_plugged else 'Not Charging'})"


def alarm_thread(text):
    sound_file = "sounds/alarm.mp3"

    pygame.init()

    try:
        # Extract time using dateparser
        alarm_time = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})

        if alarm_time is None:
            print("Could not extract a valid time. Please try again.")
            return

        print(f"Alarm set for {alarm_time.strftime('%Y-%m-%d %H:%M:%S')}")
        while True:
            now = datetime.now()
            if now >= alarm_time:
                print("Wake up! Alarm ringing!")
                pygame.mixer.music.load("sounds/alarm.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                break
            time.sleep(1)
    except Exception as e:
        print(f"An error occurred in alarm_thread: {e}")


def set_alarm(text):
    # Run the alarm in a background thread so it doesn't block the main thread.
    thread = threading.Thread(target=alarm_thread, args=(text,), daemon=True)
    thread.start()
    return "Alarm is set"


def get_weather():
    city = 'Bangalore'
    """
    Retrieves current weather data and returns a JSON-formatted string containing:
        - current_temperature_celsius: current temperature in Celsius
        - humidity_percent: humidity in percent
        - wind_speed_kmph: wind speed in kilometers per hour
        - precipitation_percent: precipitation percentage (using the forecast's 'pop' value)
        - cloudiness_percent: cloudiness in percentage
        - current_time: local current time in 12-hour format (HH:MM AM/PM)
        - chance_of_rain_percent: chance of rain in percentage (using the forecast's 'pop' value)

    Parameters:
        city (str): Name of the city for which weather data is fetched.

    Returns:
        A JSON-formatted string with the above weather details.
    """
    # Embedded API key
    api_key = "779d9b8f4622f147a67ae50d35331a38"

    # Use the forecast endpoint to get weather data
    try:
        response = requests.get(f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}")
        response.raise_for_status()
    except Exception as e:
        return json.dumps({"error": str(e)})

    data = response.json()

    # Use the first forecast entry as a proxy for current conditions
    if "list" in data and len(data["list"]) > 0:
        current_forecast = data["list"][0]
    else:
        return json.dumps({"error": "No forecast data available."})

    # Extract weather details
    temp_k = current_forecast["main"]["temp"]
    temp_c = round(temp_k - 273.15, 2)
    humidity = current_forecast["main"]["humidity"]
    wind_speed_mps = current_forecast["wind"]["speed"]
    wind_speed_kmph = round(wind_speed_mps * 3.6, 2)
    cloudiness = current_forecast["clouds"]["all"]

    # Probability of Precipitation (pop) is given as a fraction; convert it to percentage
    pop = current_forecast.get("pop", 0)
    chance_of_rain_percent = round(pop * 100, 2)

    # For this example, we'll assume precipitation percentage is the same as the chance of rain
    precipitation_percent = chance_of_rain_percent

    # Get current local time in 12-hour format
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")

    result = {
        "current_temperature_celsius": temp_c,
        "humidity_percent": humidity,
        "wind_speed_kmph": wind_speed_kmph,
        "precipitation_percent": precipitation_percent,
        "cloudiness_percent": cloudiness,
        "current_time": current_time,
        "chance_of_rain_percent": chance_of_rain_percent
    }

    return json.dumps(result, indent=4)


def whatsapp_call(name, type):
    call_type = type
    contacts = {
        "Anil": "+917289962452",
        "Mummy": "+919990667273",
        "Priya": "+918765432109"
    }
    number = contacts.get(name)
    if not number:
        print(f"Contact '{name}' not found.")
        return

    if call_type not in ["voice", "video"]:
        print("Invalid call type. Choose either 'voice' or 'video'.")
        return

    try:
        print(f"Placing a {call_type} call to {name}...")

        # Form the WhatsApp call URL based on call type
        if call_type == "voice":
            url = f"whatsapp://call?phone={number}"
        else:
            url = f"whatsapp://video?phone={number}"

        # Open the URL using subprocess
        subprocess.run(["start", url], shell=True)
    except Exception as e:
        print(f"Error: {e}")


def send_message(name, message):
    # Example contact list
    contacts = {
        "Anil": "+917289962452",
        "Mummy": "+919990667273",
        "Priya": "+918765432109"
    }

    # Check if name exists in the contacts
    number = contacts.get(name)
    if not number:
        print(f"Contact '{name}' not found.")
        return

    try:
        print(f"Opening WhatsApp Desktop to text {name}...")
        # Encode the message for URL compatibility
        encoded_message = urllib.parse.quote(message)
        subprocess.run(["start", f"whatsapp://send?phone={number}"], shell=True)

        time.sleep(2)
        # Construct the WhatsApp URL
        url = f'whatsapp://send?phone={number}&text={encoded_message}'

        # Open WhatsApp using os.startfile (Windows only)
        os.startfile(url)
        print("Opening WhatsApp...")

        # Simulate Enter key press to send the message
        time.sleep(1)  # Adjust if needed
        print("Sending the message...")
        pyautogui.press('enter')
        return "Message sent"
    except Exception as e:
        print(f"Error: {e}")


def get_time():
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    return current_time


def search_web(query):
    print(f"Searching the web for: {query}")


def set_reminder(message, datetime):
    print(f"Reminder set: '{message}' at {datetime}")


def play_music(song_name):
    try:
        print(f"Searching and playing '{song_name}' on YouTube...")
        kit.playonyt(song_name)
        print("Video is now playing.")
    except Exception as e:
        print(f"An error occurred: {e}")

def control_system(setting_type, value):
    try:
        if setting_type.lower() == "volume":
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            try:
                current_volume = volume.GetMasterVolumeLevelScalar() * 100  # Get current volume in percentage
                if isinstance(value, str):
                    # Check if it's an increase or decrease command
                    if "increase" in value.lower():
                        new_volume = min(current_volume + 20, 100)
                        volume.SetMasterVolumeLevelScalar(new_volume / 100.0, None)
                        print(f"Volume increased to {new_volume}%")
                    elif "decrease" in value.lower():
                        new_volume = max(current_volume - 20, 0)
                        volume.SetMasterVolumeLevelScalar(new_volume / 100.0, None)
                        print(f"Volume decreased to {new_volume}%")
                    else:
                        # Extract volume percentage from the input string
                        volume_percentage = int(re.sub(r"[^0-9]", "", value))
                        if 0 <= volume_percentage <= 100:
                            volume.SetMasterVolumeLevelScalar(volume_percentage / 100.0, None)
                            print(f"Volume set to {volume_percentage}%")
                        else:
                            print("Volume value must be between 0 and 100.")
                else:
                    print("Error: Value must be a string specifying volume level or action (e.g., 'increase', 'decrease', or an exact volume percentage).")
            finally:
                # Explicitly release the COM object to prevent access violation errors during garbage collection.
                if volume is not None:
                    volume.Release()

        elif setting_type.lower() == "brightness":
            current_brightness = sbc.get_brightness()[0]  # Assuming a single monitor
            if isinstance(value, str):
                # Check if it's an increase or decrease command
                if "increase" in value.lower():
                    new_brightness = min(current_brightness + 20, 100)
                    sbc.set_brightness(new_brightness)
                    print(f"Brightness increased to {new_brightness}%")
                elif "decrease" in value.lower():
                    new_brightness = max(current_brightness - 20, 0)
                    sbc.set_brightness(new_brightness)
                    print(f"Brightness decreased to {new_brightness}%")
                else:
                    # Extract brightness percentage from the input string
                    brightness_percentage = int(re.sub(r"[^0-9]", "", value))
                    if 0 <= brightness_percentage <= 100:
                        sbc.set_brightness(brightness_percentage)
                        print(f"Brightness set to {brightness_percentage}%")
                    else:
                        print("Brightness value must be between 0 and 100.")
            else:
                print("Error: Value must be a string specifying brightness level or action (e.g., 'increase', 'decrease', or an exact brightness percentage).")
        else:
            print("Invalid setting type. Please use 'volume' or 'brightness'.")
    except Exception as e:
        print(f"Error: {e}")


def open_system_app(app_name):
    if platform.system() != "Windows":
        print("This function is only for Windows.")
        return

    apps = {
        "terminal": ["start", "cmd"],  # Replaced powershell with wt (Windows Terminal)
        "task manager": ["taskmgr"],
        "notepad": ["notepad"],
        "explorer": ["explorer"],
        "control panel": ["control"],
        "settings": ["explorer", "ms-settings:"],
        "calculator": ["calc"],
        "wifi": ["explorer", "ms-settings:network-wifi"],
        "bluetooth": ["explorer", "ms-settings:bluetooth"],
        "diskmgmt": ["diskmgmt.msc"],
        "camera": ["explorer", "microsoft.windows.camera:"],
    }

    app_name = app_name.lower()
    if app_name in apps:
        command = apps[app_name]
        try:
            # Use shell=True to handle file associations and UWP apps properly
            subprocess.run(command, check=True, shell=True)
            print(f"Successfully launched {app_name}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to launch {app_name}. Error: {e}")
        except Exception as e:
            print(f"Unexpected error opening {app_name}: {e}")
    else:
        print(f"Application '{app_name}' is not recognized.")

