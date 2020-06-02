# Annotate audio
These python helper scripts help you to get smaller annotated audio files, from a large audio containing file, to train STT or TTS models, by:
    1. split the large file in several smaller wav files, separated by silence
    2. (optional) get transcription for these smaller audio files from google cloud STT service, this requires a GCP account
    3. manually annotate (or correct GCP annotations) the smaller audio files
    
## Installation
Step 1 requires to have [ffmpeg](https://www.ffmpeg.org/download.html) installed on your system.  
All the scripts are written in Python 3.6+, required packages can be installed with:
```
pip install -r requirements.txt
```
You will need [pyaudio](https://people.csail.mit.edu/hubert/pyaudio/#downloads) for step 3.  

Additionnally, if you want to use GCP's STT you should install their python client with
```
pip install --upgrade google-cloud-speech
```
and configure a project [as shown here](https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries?hl=fr#client-libraries-install-python).  

## Usage
1.
```
python split.py --input big_file.wav --audio_folder audio --out_csv sentences.csv
```
sentences.csv file will be formated as "file;sentence".  

2.
```
python get_gcp_transcription.py --audio_folder audio --csv sentences.csv --language_code fr-Fr
```

3.
```
python annotate.py --audio_folder audio --csv sentences.csv
```

For all three scripts, you can see additional arguments with 
```
python FILE_NAME.py -h
```