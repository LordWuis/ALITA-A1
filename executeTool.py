import re
# --------------------
# Importing Tools
# --------------------
from tools import (send_message,
                   whatsapp_call,
                   control_system,
                   get_time,
                   get_weather,
                   system_check,
                   play_music,
                   open_system_app,
                   set_alarm,
                   set_reminder,
                   search_web)


def extract_function_name(call_str):
    """ Extract the function name from a call like set_reminder("msg", "time") """
    match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\(", call_str)
    return match.group(1) if match else None


def execute_function_call(call_str):
    try:
        text = re.sub(r'^\s+|\s+$', '', call_str)
        func_name = extract_function_name(text)

        if func_name not in function_map:
            print(f"Error: Function '{func_name}' is not defined.")
            return

        print(f"Executing: {call_str}")
        result = eval(call_str, {"__builtins__": {}}, function_map)
        return result
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


function_map = {
    "get_weather": get_weather,
    "get_time": get_time,
    "open_system_app": open_system_app,
    "send_message": send_message,
    "search_web": search_web,
    "set_reminder": set_reminder,
    "play_music": play_music,
    "system_check": system_check,
    "set_alarm": set_alarm,
    "whatsapp_call": whatsapp_call,
    "control_system": control_system
}