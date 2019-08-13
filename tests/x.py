import speech_recognition as sr
import os
import time

r = sr.Recognizer()
with sr.Microphone() as source:
    r.pause_threshold = 1
    r.adjust_for_ambient_noise(source, duration = 1)
    print("Speak:")
    audio = r.listen(source)  # recording

try:
    print("You said " + r.recognize_sphinx(audio))    # recognize speech using CMUsphinx Speech Recognition - OFFLINE
except LookupError:                            # speech is unintelligible
    print("Could not understand audio")
