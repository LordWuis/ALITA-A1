import re

def detect_intent(query):
    query = query.lower().strip()

    # ✅ Define intent categories with diverse and expanded keywords
    tool_keywords = {
        "communication": ["call", "message", "email", "text", "ping", "whatsapp", "send", "contact", "chat", "talk", "reach out", "write", "dial"],
        "reminder": ["remind", "reminder", "schedule", "notify", "alert", "don't forget", "set reminder", "prompt", "tell me", "alert me", "notify me", "mark", "book"],
        "alarm": ["alarm", "wake", "ring", "set alarm", "remind me to wake", "wake me up", "sound the alarm", "set an alarm", "reminder to wake"],
        "weather": ["weather", "forecast", "temperature", "climate", "rain", "snow", "sunny", "weather report", "humidity", "wind", "forecast today", "how's the weather", "is it hot", "is it cold"],
        "time": ["time", "clock", "current time", "what time", "now", "time check", "what's the time", "how late is it", "what's the hour", "tell me the time", "when is it"],
        "search": ["search", "google", "lookup", "find", "browse", "explore", "look up", "search for", "look into", "check", "find out", "search online", "investigate"],
        "open": ["open", "launch", "start", "access", "begin", "run", "execute", "open app", "open website", "start program", "show me", "bring up", "initiate", "load"],
        "music": ["play", "song", "music", "playlist", "track", "tune", "radio", "listen", "hear", "put on", "start playing", "turn on music", "play a song", "play my playlist"],
        "task": ["task", "do", "complete", "finish", "perform", "carry out", "take care of", "handle", "take on", "execute", "complete task", "make", "set", "increase", "decrease"],
        "note": ["note", "write", "jot down", "take note", "make a note", "remember", "save this", "write down", "remind me", "note this"],
        "question": ["question", "ask", "inquire", "wonder", "doubt", "query", "what", "how", "who", "why", "when", "tell me", "can you explain", "what is", "give me"],
        "settings": ["settings", "preferences", "configuration", "set up", "adjust", "change", "customize", "modify", "personalize", "update", "set", "manage settings"],
    }

    # ✅ Negation check (Prevent false positives for negative queries)
    if re.search(r"\b(don't|do not|cancel|stop|never)\b", query):
        return False

    # ✅ Pattern matching for diverse intent recognition with flexibility
    for intent, keywords in tool_keywords.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", query):
                return True

    return False