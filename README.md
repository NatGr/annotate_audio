# Annotate audio
These python helper scripts help you to get smaller annotated audio files, from a large audio containing file, to train STT or TTS models, by:
    1. split the large file in several smaller wav files, separated by silence. If there are several speaker in your audio, you can also remove the parts spoken by the other(s) speaker(s).
    2. (optional) get transcription for these smaller audio files from google cloud STT service, this requires a GCP account
    3. manually annotate (or correct GCP annotations) the smaller audio files
    
## Installation
Step 1 requires to have [ffmpeg](https://www.ffmpeg.org/download.html) installed on your system.  
All the scripts are written in Python 3.6+, required packages can be installed with:
```
pip install -r requirement.txt
```
You will need [pyaudio](https://people.csail.mit.edu/hubert/pyaudio/#downloads) for step 3.  

Additionnally, if you want to use GCP's STT you should install their python client with
```
pip install --upgrade google-cloud-speech
```
and configure a project [as shown here](https://cloud.google.com/docs/authentication/getting-started).  
The current version of this script is compatible with google-cloud-speech 2.X, if you want to use version 1.X, you can have a look at previous versions of this repo which used that version as well.

## Usage
1.
```
python split.py --input big_file.wav --audio_folder audio --out_csv sentences.csv
```
sentences.csv file will be formated as "file;sentence".   
To keep only files spoken by a particular speaker, use the "--remove_bad_segments" and "--speaker_segment" arguments.  

2.
```
python get_gcp_transcription.py --audio_folder audio --csv sentences.csv --language_code en-US
```

3.
```
python annotate.py --audio_folder audio --csv sentences.csv
```

For all three scripts, you can see additional arguments with 
```
python FILE_NAME.py -h
```
