# Code taken from StackOverflow and modified
# https://stackoverflow.com/questions/18406570/python-record-audio-on-detected-sound
# Written by:-  https://stackoverflow.com/users/1185894/ederwander


import pyaudio
import math
import struct
import wave
import sys
import time
import uuid

#Assuming Energy threshold upper than 30 dB
Threshold = 15
silence_threshold = 4

SHORT_NORMALIZE = (1.0/32768.0)
chunk = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
swidth = 2
Max_Seconds = 10
# TimeoutSignal=int((RATE / chunk * Max_Seconds) + 2)
TimeoutSignal = 0
silence = True
FileNameTmp = 'gpt_quest.wav'
Time=1
all =[]

def GetStream(chunk):
    return stream.read(chunk)
def rms(frame):
    count = len(frame)/swidth
    format = "%dh"%(count)
    # short is 16 bit int
    shorts = struct.unpack( format, frame )

    sum_squares = 0.0
    for sample in shorts:
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n
    # compute the rms 
    rms = math.pow(sum_squares/count,0.5);
    # print(rms*100)
    return rms * 100

def WriteSpeech(WriteData):
    # stream.stop_stream()
    # stream.close()
    # p.terminate()
    FileNameTmp = uuid.uuid4().hex + '.wav'
    wf = wave.open(FileNameTmp, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(WriteData)
    wf.close()
    return FileNameTmp

def KeepRecord(TimeoutSignal, LastBlock):
    global all
    all.append(LastBlock)
    silence_counter = 0
    while not TimeoutSignal:
        try:
            data = GetStream(chunk)
            rms_value = rms(data)
            all.append(data)
            if (rms_value < silence_threshold):
                # print("Silence Detected")
                time.sleep(0.2)
                if silence_counter > 10:
                    TimeoutSignal = 1
                silence_counter = silence_counter + 1
            else:
                silence_counter = 0

        except KeyboardInterrupt:
            break
        except:
            continue

    data = b''.join(all)
    # print("Writing to File")
    filename = WriteSpeech(data)
    all = []
    return filename
    # listen(silence) 

# def listen(silence):
#     print("waiting for Speech")
#     while silence:
#         try:
#             input = GetStream(chunk)
#         except KeyboardInterrupt:
#             break
#         except:
#             continue
#         rms_value = rms(input)
#         if (rms_value > Threshold):
#             silence=False
#             LastBlock=input
#             print("Recording....")
#             KeepRecord(TimeoutSignal, LastBlock)
    
def listen(silence):
    print("Listening!")
    try:
        input = GetStream(chunk)
    except:
        exit(0)

    rms_value = rms(input)
    if (rms_value > Threshold):
        LastBlock=input
        print("Recording....")
        filename = KeepRecord(TimeoutSignal, LastBlock)
        return filename

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
    channels = CHANNELS,
    rate = RATE,
    input = True,
    output = True,
    frames_per_buffer = chunk)

# listen(silence)