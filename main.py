import time
import threading
import re
import queue
import pyaudio
import numpy as np
import speech_recognition as sr
from kokoro import KPipeline
import ollama
import datetime
from groq import Groq
import os
from dotenv import load_dotenv
import keyboard


# Load environment variables from .env file
load_dotenv()
# --------------------
# Other files
# --------------------
from detectIntent import detect_intent as di
from executeTool import execute_function_call as ex

# ---------------------------
# Decision LLM initialization
# ---------------------------
client = Groq(
    api_key=os.getenv("API_KEY"),
)


def get_greeting():
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good Morning"
    elif hour < 18:
        return "Good Afternoon"
    else:
        return "Good Evening"

# ------------------------------------------------------------------------------
# Global Variables and Thread-safe Queues
# ------------------------------------------------------------------------------


cancel_event = threading.Event()
query_queue = queue.Queue()          # Queue for incoming queries
sentence_queue = queue.Queue()       # Queue for complete sentences from LLM

WAKE_WORD = "alita"
USER = "Lord"
is_sleeping = True
sleep_timer = None


def start_sleep_timer():
    global sleep_timer
    if sleep_timer:
        sleep_timer.cancel()  # Reset timer if a new query arrives
    print("⏳ Sleep timer started. Going to sleep in 2 minutes...")
    sleep_timer = threading.Timer(120, go_to_sleep)
    sleep_timer.start()


def go_to_sleep():
    global is_sleeping
    print("😴 LLM is now asleep due to inactivity.")
    is_sleeping = True


# Conversation history for LLM interaction
messages = [{
    "role": "system",
    "content": (
        "You are a highly intelligent assistant. "
        "You always answer what is asked. "
        "Always answer in the shortest possible manner yet engaging."
        "You add punctuations like (.!?) in your response frequently."
    )
}]

# ------------------------------------------------------------------------------
# InstantTTS Class Definition
# ------------------------------------------------------------------------------


class InstantTTS:
    """
    Synchronous TTS using KPipeline. Handles audio stream setup and synchronous speech.
    """
    def __init__(self, voice="af_heart"):
        self.voice = voice
        self.pipeline = KPipeline(lang_code='a')
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=24000,
            output=True,
            frames_per_buffer=16  # Reduced frame size for lower latency
        )

    def speak_sync(self, text, speed=1.2):
        """Synchronously generate and play TTS audio for a sentence."""
        try:
            for _, _, audio in self.pipeline(text, voice=self.voice, speed=speed):
                if cancel_event.is_set():
                    break
                if audio is not None:
                    audio_chunk = audio.cpu().numpy().squeeze().astype(np.float32)
                    if not self.stream.is_active():
                        try:
                            self.stream.start_stream()
                        except Exception:
                            continue
                    self.stream.write(audio_chunk.tobytes())
        except Exception as e:
            print(f"TTS error: {e}")

    def __del__(self):
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'p'):
            self.p.terminate()


# Create an instance of InstantTTS
tts = InstantTTS(voice="af_bella")

# ------------------------------------------------------------------------------
# LLM Response Streaming
# ------------------------------------------------------------------------------

sentence_endings = re.compile(r'(?<=[.!?])\s+')
def stream_generate_response(query):
    """
    Streams response from LLM and buffers complete sentences into sentence_queue.
    """
    global messages
    cancel_event.clear()  # Reset cancel flag
    print(f"\n🔎 Generating response for: {query}")

    if di(query):
        print("This query involves a tool action.")
        chat_completion = client.chat.completions.create(
            #
            # Required parameters
            #
            messages=[
                # Set an optional system message.
                {
                    "role": "system",
                    "content": """You are a highly intelligent Tool Manager. Your job is to analyze query and determine 
                       if it requires the use of one of the following tools. For each tool, follow the instructions below.
                       If a query is identified as needing a tool, return the function name along with the parameters 
                       (filled appropriately) exactly as shown in the examples.
                        If the query does not require the use of any tool, simply respond with: "no tool required"

           Tools & Instructions:
           *search_web('query')

           When to use: Use this tool when the query requests real-time information or current events data, especially 
           information post-2024.

           Example Variations:

           Query: "What's the latest update on Mars colonization?"
           Output: search_web("latest update on Mars colonization")

           Query: "Tell me the recent tech trends in 2025."
           Output: search_web("recent tech trends 2025")

           *send_message('recipient name', 'message')

           When to use: Use this tool when the query instructs to send a text message to someone.

           Example Variations:

           Query: "Tell Anil I will be late today."
           Output: send_message("Anil", "I will be late today")

           Query: "Send a quick hello to Sarah."
           Output: send_message("Sarah", "hello")

           *whatsapp_call('recipient name', 'type of call')

           When to use: Use when the query instructs to initiate a WhatsApp call with someone.

           Example Variations:

           Query: "Call John now."
           Output: whatsapp_call("John", "voice")

           Query: "I need to make a call to Priya."
           Output: whatsapp_call("Priya", "voice")

           Query: "make a video call to Priya."
           Output: whatsapp_call("Priya", "video")

           Query: "Place a video call to Rahul."
           Output: whatsapp_call("Rahul", "video")

           *read_emails()

           When to use: Use when the query requests to check for new or unread emails.

           Example Variations:

           Query: "Check my emails."
           Output: read_emails()

           Query: "Do I have any new emails?"
           Output: read_emails()

           *send_emails('recipient name', 'message')

           When to use: Use when the query instructs to send an email. Include recipient name, and message body.

           Example Variations:

           Query: "Email Aryan and say 'The meeting is rescheduled to 3 PM'."
           Output: send_emails("Aryan", "The meeting is rescheduled to 3 PM")

           Query: "Send an email to Ajay, message 'Let's meet for lunch tomorrow.'"
           Output: send_emails("Ajay", "Let's meet for lunch tomorrow")

           *set_reminder('time', message')

           When to use: Use when the query instructs to set a reminder.

           Example Variations:

           Query: "Remind me to call mom at 6 PM."
           Output: set_reminder("6 PM", "You were supposed to call your mom now.")

           Query: "Set a reminder: Buy groceries in the evening."
           Output: set_reminder("evening","Lets go Buy groceries")

           *set_alarm(time)

           When to use: Use when the query instructs to set an alarm.

           Example Variations:

           Query: "Set an alarm for 7 AM tomorrow."
           Output: set_alarm("7 AM")

           Query: "I need an alarm at 06:30."
           Output: set_alarm("06:30")

           *play_music('song_name')

           When to use: Use when the query instructs to play a specific song.

           Example Variations:

           Query: "Play 'Imagine' by John Lennon."
           Output: play_music("Imagine")

           Query: "I want to listen to 'Bohemian Rhapsody'."
           Output: play_music("Bohemian Rhapsody")

           *system_check()

           When to use: Use when the query instructs to run a system diagnostic or check.

           Example Variations:

           Query: "How is the system performing? Do a system check."
           Output: system_check()

           Query: "Run a diagnostic to see if everything's okay."
           Output: system_check()

           *get_weather()

           When to use: Use when the query asks directly or indirectly about weather updates.

           Example Variations:

           Query: "What's the weather like today?"
           Output: get_weather()

           Query: "Do I need an umbrella? What's the weather?"
           Output: get_weather()

           *get_time()

           When to use: Use when the query asks for the current time.

           Example Variations:

           Query: "What's the time now?"
           Output: get_time()

           Query: "Tell me the current time."
           Output: get_time()

           *open_system_app('app_name')

           When to use: Use when the query instructs to open a specific system application.

           Example Variations:

           Query: "Open the calculator."
           Output: open_system_app("calculator")

           Query: "I need to launch the calendar app."
           Output: open_system_app("calendar")

           *control_system("setting_type", "value")

           When to use: Use when the query instructs to increase/decrease/set volume or brightness.

           Example Variations:

           Query: "decrease the brightness 50"
           Output: control_system("brightness", "50%")

           Query: "decrease the brightness"
           Output: control_system("brightness", "decrease")

           Query: "increase the brightness to 80"
           Output: control_system("brightness", "80%")

           Query: "set brightness to full"
           Output: control_system("brightness", "100%")

           Query: "increase the volume to 80"
           Output: control_system("volume", "80%")

           Query: "decrease the volume"
           Output: control_system("volume", "decrease")

           Query: "increase the volume"
           Output: control_system("volume", "increase")

           Query: "decrease the volume to 40"
           Output: control_system("volume", "40%")

           Query: "set volume to full"
           Output: control_system("volume", "100%")

           **Overall Instructions:
               -Analyze the query:
               First, determine if the user's query requires a tool to be used based on the above criteria.

               -If a tool is required:
               Output the function call with the appropriate parameters filled in, exactly as in the examples above.

               -If no tool is required:
               Simply output: "no tool required"
           """
                },
                # Set a user message for the assistant to respond to.
                {
                    "role": "user",
                    "content": f"query: {query}"
                }
            ],

            # The language model which will generate the completion.
            model="llama3-70b-8192",

            temperature=0,

            max_completion_tokens=1024,

            top_p=1,

            stop=None,

            stream=False,
        )

        tool_response = ex(chat_completion.choices[0].message.content)
        print(f"tool response: {tool_response}")

        try:
            response_generator = ollama.chat(
                model="helper",
                messages=[{'role': 'user', 'content': f'Data: {tool_response}, query: {query}'}],
                options={'num_gpu_layers': 50},
                stream=True
            )

            buffer = ""
            for chunk in response_generator:
                token = chunk['message']['content']
                buffer += token

                # Check for sentence completion using regex
                while True:
                    match = sentence_endings.search(buffer)
                    if not match:
                        break

                    # Extract sentence up to the matched punctuation
                    sentence = buffer[:match.end()].strip()
                    buffer = buffer[match.end():]

                    if sentence:
                        sentence_queue.put(sentence)
                        print("Queued sentence:", sentence)

            # Queue any remaining text in the buffer
            if buffer.strip():
                sentence_queue.put(buffer.strip())
                print("Queued sentence:", buffer.strip())
        except Exception as e:
            print(f"Text generation error: {str(e)}")
    else:
        print("This query does not involve a tool action.")
        try:
            response_generator = ollama.chat(
                model="chatbot",
                messages=[{'role': 'user', 'content': f'query: {query}'}],
                options={'num_gpu_layers': 50},
                stream=True
            )

            buffer = ""
            for chunk in response_generator:
                token = chunk['message']['content']
                buffer += token

                # Check for sentence completion using regex
                while True:
                    match = sentence_endings.search(buffer)
                    if not match:
                        break

                    # Extract sentence up to the matched punctuation
                    sentence = buffer[:match.end()].strip()
                    buffer = buffer[match.end():]

                    if sentence:
                        sentence_queue.put(sentence)
                        print("Queued sentence:", sentence)

            # Queue any remaining text in the buffer
            if buffer.strip():
                sentence_queue.put(buffer.strip())
                print("Queued sentence:", buffer.strip())
        except Exception as e:
            print(f"Text generation error: {str(e)}")

# ------------------------------------------------------------------------------
# Background Processing Functions
# ------------------------------------------------------------------------------


def monitor_and_process():
    """Continuously monitors sentence_queue and processes sentences with TTS."""
    while True:
        try:
            sentence = sentence_queue.get(timeout=0.1)  # Wait for a sentence
            print(f"\nProcessing: {sentence}")
            tts.speak_sync(sentence)
        except queue.Empty:
            continue


def generation_worker():
    """Processes queries from query_queue and triggers LLM response streaming."""
    while True:
        query = query_queue.get()
        if query is None:  # Allow graceful shutdown if needed
            break
        stream_generate_response(query)


def listen_for_query():
    global is_sleeping
    """
    Listens continuously for user speech input and enqueues valid queries.
    Commands containing "Siri" are checked for a "stop" command.
    """
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("🎤 Listening... Speak now!")
        while True:
            try:
                audio = recognizer.listen(source, timeout=1)
                text = recognizer.recognize_google(audio)
                print(f"You said: {text}")
                keyboard.send('stop media')
                if WAKE_WORD in text.lower():
                    print(f"{WAKE_WORD} is awake now.")
                    is_sleeping = False
                print(f"📝 {text}")
                if not is_sleeping:
                    if "stop" in text.lower():
                        cancel_event.set()
                        print("\n🛑 Stopped the current generation. Listening for the next query.")
                        continue
                    if text.lower() != WAKE_WORD:
                        add_query(text)
                    else:
                        tts.speak_sync(f"{get_greeting()}, {USER}")
                    start_sleep_timer()
                else:
                    print("Sleeping...")
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError:
                print("⚠ Could not connect to Google's Speech API.")


def add_query(query):
    """
    Stops any ongoing generation and enqueues a new query.
    """
    print("\n⛔ Stopping previous generation (if any)...")
    cancel_event.set()
    time.sleep(0.1)
    query_queue.queue.clear()  # Clear any previous queries
    query_queue.put(query)
    print("✅ New query submitted.")

# ------------------------------------------------------------------------------
# Main Function: Start Threads and Listen for Queries
# ------------------------------------------------------------------------------


def main():
    # Start thread to process sentences with TTS
    threading.Thread(target=monitor_and_process, daemon=True).start()
    # Start thread for LLM generation worker
    threading.Thread(target=generation_worker, daemon=True).start()
    # Start listening for queries (blocking call)
    listen_for_query()


if __name__ == '__main__':
    main()

# Keep the main thread alive if needed (not necessary in this structure)
