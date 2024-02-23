from openai import OpenAI
from dotenv import load_dotenv
from playsound import playsound
import cv2, os, requests, base64, time
import uuid, math, struct, wave, pyaudio, threading

# Loading pre-requisites ==========================
load_dotenv()

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
client = OpenAI()

vid = cv2.VideoCapture(2)
base64Frames = []


# Audio Setting ===================================
Threshold = 15
silence_threshold = 4
SHORT_NORMALIZE = (1.0/32768.0)
chunk = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
swidth = 2
TimeoutSignal = 0
silence = True
Time=1
all =[]
processing_flag = False
initial_rms_config = 0

# Defining Supporting Functions ================================
def GetStream(chunk):
    if stream.is_stopped(): # 
        stream.start_stream()
    return stream.read(chunk)

def rms(audio_frames):
    count = len(audio_frames)/swidth
    format = "%dh"%(count)
    # short is 16 bit int
    shorts = struct.unpack( format, audio_frames )

    sum_squares = 0.0
    for sample in shorts:
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n
    # compute the rms
    # if not initial_rms_config:
    #     initial_rms_config = sum_squares/count
    rms = math.pow(sum_squares/count,0.5);
    print(rms*100)
    return rms * 100

def WriteSpeech(WriteData):
    global stream
    stream.stop_stream()
    # stream.close()
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
    global silence_threshold
    global filename
    global processing_flag
    global chunk

    processing_flag = True
    all.append(LastBlock)
    silence_counter = 0
    time.sleep(0.2)
    while not TimeoutSignal:
        try:
            data = GetStream(chunk)
            rms_value = rms(data)
            all.append(data)
            if (rms_value < silence_threshold):
                print("Silence Detected")
                time.sleep(0.2)
                if silence_counter > 5:
                    TimeoutSignal = 1
                silence_counter = silence_counter + 1
            else:
                silence_counter = 0

        except KeyboardInterrupt:
            break
        except:
            continue

    data = b''.join(all)
    all = []
    print("Writing to File")
    filename = WriteSpeech(data)
    transcript_text = transcribing()
    collect_additional_frames()
    gpt_response = asking_gpt(transcript_text)
    tts(gpt_response)
    processing_flag = False
    return

def collect_additional_frames():
    global base64Frames
    global frame
    print("Collecting frames!")
    while len(base64Frames)<=700:
        _, buffer = cv2.imencode(".jpeg", frame)
        base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

def transcribing():
    global filename
    global base64Frames
    if len(base64Frames) >= 700:
        # Code to ask the question to GPT-4 using voice
        print("Transcribing!")

        transcript = client.audio.transcriptions.create(
        model="whisper-1", 
        file=open(filename, "rb")
        )
        return transcript.text
    
def asking_gpt(transcript_text):
    print("Asking GPT!")

    PROMPT_MESSAGES = [
        {
            "role": "user",
            "content": [
                f"Explain following frames with the following context {transcript_text} in one line only! Do not write anything unnecessary!",
                *map(lambda x: {"image": x, "resize": 768}, base64Frames[0::int(len(base64Frames) / 20)]),
            ],
        },
    ]

    params = {
        "model": "gpt-4-vision-preview",
        "messages": PROMPT_MESSAGES,
        "max_tokens": 200,
    }


    result = client.chat.completions.create(**params)
    print(result.choices[0].message.content)
    return result.choices[0].message.content

def tts(gpt_response):
    global base64Frames
    response = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        },
        json={
            "model": "tts-1-1106",
            "input": gpt_response,
            "voice": "onyx",
        },
    )

    audio = b""

    for chunky in response.iter_content(chunk_size=1024 * 1024):
        audio += chunky


    with open(f"{filename}_gpt_reply.wav", 'wb') as f:
        f.write(audio)

    print("Making GPT talk!")
    playsound(f"{filename}_gpt_reply.wav")
    base64Frames = []


if __name__ == '__main__':
    p = pyaudio.PyAudio()

    stream = p.open(format = FORMAT,
        channels = CHANNELS,
        rate = RATE,
        input = True,
        output = True,
        frames_per_buffer = chunk)
    
    # threading.Thread(target=vid_capture_show).start()

    while(True):
        ret, frame = vid.read()
        cv2.imshow('frame', frame)
        _, buffer = cv2.imencode(".jpeg", frame)
        base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

        if not processing_flag:
            # print("Listening!")
            try:
                input = GetStream(chunk)
            except Exception as e:
                print(e)
                exit(0)
            rms_value = rms(input)
            if (rms_value > Threshold):
                print(rms_value)
                base64Frames = base64Frames[-50:]
                LastBlock=input
                print("Recording....")
                # filename = KeepRecord(TimeoutSignal, LastBlock)
                record_audio = threading.Thread(target=KeepRecord, args=(TimeoutSignal,LastBlock,)).start()

                
    
        
        # the 'q' button is set as the quitting button
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break
    
        
    try:
        if record_audio.active():
            record_audio.join()
    except:
        pass

    # After the loop release the cap object
    vid.release() 
    # Destroy all the windows 
    cv2.destroyAllWindows() 