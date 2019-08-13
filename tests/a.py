#!/usr/bin/env python3
# coding: utf-8

# In[ ]:

import speech_recognition as sr  
import playsound # to play saved mp3 file 
from gtts import gTTS # google text to speech 
import os
import webbrowser
import serial
import time
import datetime
import itertools
now = datetime.datetime.now()
#ArduinoSerial = serial.Serial('COM5',9600)
num = 1
def assistant_speaks(output): 
    global num 
  
    # num to rename every audio file  
    # with different name to remove ambiguity 
    num += 1
    print("PerSon : ", output) 
  
    toSpeak = gTTS(text = output, lang ='en', slow = False) 
    # saving the audio file given by google text to speech 
    file = str(str(num)+".mp3") 
    toSpeak.save(file) 
      
    # playsound package is used to play the same file. 
    playsound.playsound(file, True)  
    os.remove(file)
def get_audio(): 
  
    rObject = sr.Recognizer() 
    audio = '' 
  
    with sr.Microphone() as source: 
        print("Speak...") 
          
        # recording the audio using speech recognition 
        audio = rObject.listen(source, phrase_time_limit = 5)  
        print("Stop.") # limit 5 secs 
  
        try:
            text = rObject.recognize_sphinx(audio, language ='en-US') 
            print("You : ", text) 
        except:
            print("error sphinx")
            
        return text 

def home():
    assistant_speaks("Who all are there at your home?")
    fam=""
    no=""
    fam=get_audio().lower()

    a=['mum','dad']
    b=['mum','dad','sister']
    for p in itertools.permutations(a):
        a=(p[0]+" "+'and'+ " " + p[1]);
        if(fam==a):
            assistant_speaks("Thats great!Don't you have siblings?");
            no=get_audio()
            assistant_speaks("OK");
            return
    for p in itertools.permutations(b):
        b=(p[0]+" "+p[1]+" " +'and'+ " " + p[2]);       
        if(fam==b):
            assistant_speaks("Thats great!");
            return
            
def process_text(input): 
    try:
        if "who are you" in input or "define yourself" in input: 
            speak = '''Hello, I am Person. Your personal Assistant. 
            I am here to make your life easier. '''
            assistant_speaks(speak) 
            return          
  
        elif "who made you" in input or "created you" in input: 
            speak = "I have been created by Chythra."
            assistant_speaks(speak) 
            return
        
        elif "how are you" in input:
            speak = "I am fine."
            assistant_speaks(speak)
            return
  
        elif ("ask something about me" in input.lower()):
            ans=home();
            return
        
        elif "time now" in input:
            assistant_speaks(now.strftime("The time is %H:%M"));
            return
        
        elif 'youtube' in input.lower():
            webbrowser.get("http://www.youtube.com/results?search_query =" + '+'.join(input))
            return

        elif "exit" in input or "bye" in input:
            speak = "OK Bye"            
            assistant_speaks(speak) 
            return
            
        else: 
            webbrowser.open_new('www.google.com/search?q=' + input)
            return
    except : 
        assistant_speaks("I don't understand")  
        return 
rObject = sr.Recognizer()
while(1):
    if(get_audio()=="hi there"):
        try:
            assistant_speaks("What can i do for you?")
            text=get_audio();
            if(text!=0):
                process_text(text);
                pass;
            elif(text ==0): 
                pass;
        except:
            pass
    else:
        pass

