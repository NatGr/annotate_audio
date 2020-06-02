import argparse
import os
import pandas as pd
from tqdm import tqdm
from pydub import AudioSegment
import subprocess
import re


if __name__ == "__main__":
    parser = argparse.ArgumentParser("""Extracts audio, and splits it into smaller files""")
    parser.add_argument("--input", help="big audio file", required=True)
    parser.add_argument("--audio_folder", 
        help="folder that will contain smaller the audio files", required=True)
    parser.add_argument("--out_csv", help="name of the output csv file, that will contain the name of each smaller file and that is destined to be filled with their transcript", required=True)
    parser.add_argument("--wav_args", help="list of arguments of the wav created files as string",
                        default="-acodec pcm_s16le -ac 1 -ar 22050")
    args = parser.parse_args()
    csv_file = {"file": []}
    
    if not os.path.exists(args.audio_folder):
        os.makedirs(args.audio_folder)
    params_list = [item for param in args.wav_args.split("-")[1:] for item in f"-{param}".split(" ")[:2]]

    file_extension = os.path.splitext(args.input)[1][1:]
    full_audio = AudioSegment.from_file(args.input, file_extension)
    
    process = subprocess.run(['ffmpeg', '-i', args.input, '-af', 'silencedetect=noise=-40dB:d=0.3', '-f', 'null', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    silences = re.findall("\[silencedetect .{17} silence_start: (\d+(?:.\d*))\\n\[silencedetect .{17} silence_end: (\d+(?:.\d*))", process.stderr)
    
    # a sentence is separated by two silences, so we ignore what is before the first and after the last silence
    sentences = []
    margin = 250  # 250 ms of silence before and after speech for safety
    sent_start = float(silences[0][1]) * 1000 - margin  # sec to ms
    
    for index, (sil_start, sil_end) in tqdm(enumerate(silences[1:]), 
    desc="writing csv files", total=len(silences)-1):
        sent_end = float(sil_start) * 1000 + margin
        audio = full_audio[sent_start:sent_end]
        sent_start = float(sil_end) * 1000 - margin
        
        file_name = f"sentence_{index}.wav"
        csv_file["file"].append(file_name)
        audio.export(os.path.join(args.audio_folder, file_name), format="wav", parameters=params_list)
        
    csv_file["sentence"] = [""] * len(csv_file["file"])  # adding an empty column
    pd.DataFrame(csv_file).to_csv(args.out_csv, sep=";", index=False)
