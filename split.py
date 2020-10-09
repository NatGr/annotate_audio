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
                        default="-acodec pcm_s16le -ac 1 -ar 16000")
    parser.add_argument("--max_duration", help="maximum duration (in seconds) a clip can last", default=7, type=int)
    parser.add_argument("--min_duration", help="maximum duration (in seconds) a clip can last", default=2, type=int)
    parser.add_argument("--remove_bad_segments", action="store_true", help="set this argument if you want to automatically remove the sentences that do not seem to be spoken by the speaker of interest (which need to be specified using the 'speaker_segment' argument")
    parser.add_argument("--speaker_segment", nargs=2, type=float, 
        help="start and end time of a sample spoken by a speaker (seconds)")
    args = parser.parse_args()
    
    if not os.path.exists(args.audio_folder):
        os.makedirs(args.audio_folder)
    params_list = [item for param in args.wav_args.split("-")[1:] for item in f"-{param}".split(" ")[:2]]

    file_extension = os.path.splitext(args.input)[1][1:]
    full_audio = AudioSegment.from_file(args.input, file_extension)
    
    # find out long, medium and small silences
    # (type, noise_tol, noise_dur) for long, medium and small silences
    silence_params = [(2, -50, .5), (1, -35, .3), (0, -25, .15)]
    silences = []
    for sil_type, noise_tol, noise_dur in silence_params:
        process = subprocess.run(['ffmpeg', '-i', args.input, '-af', f'silencedetect=noise={noise_tol}dB:d={noise_dur}', '-f', 'null', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        curr_silences = re.findall("\[silencedetect .{17} silence_start: (\d+(?:.\d*))\\n\[silencedetect .{17} silence_end: (\d+(?:.\d*))", process.stderr)
        silences.extend([(float(s[0]), float(s[1]), sil_type) for s in curr_silences])
    
    silences.sort(key=lambda x: x[0])
    
    # loads necessary data if we want to remove bad speakers
    if args.remove_bad_segments:
        from resemblyzer import normalize_volume, VoiceEncoder
        from resemblyzer.hparams import sampling_rate, audio_norm_target_dBFS
        from pydub.playback import play
        import matplotlib.pyplot as plt
        import librosa
        import numpy as np
        wav, source_sr = librosa.load(args.input, sr=None)
        wav = librosa.resample(wav, source_sr, sampling_rate)
        wav = normalize_volume(wav, audio_norm_target_dBFS, increase_only=True)
        
        speaker_wav = wav[int(args.speaker_segment[0] * sampling_rate):int(args.speaker_segment[1] * sampling_rate)]
    
        print("Playing the selected audio segment at given offsets to check it is alright")
        audio = AudioSegment.from_wav(args.input)
        play(audio[int(args.speaker_segment[0]*1000):int(args.speaker_segment[1]*1000)])
        if input("Is this correct? (y/n)\n") != "y":
            exit(0)
            
        encoder = VoiceEncoder("cpu")
        speaker_embed = encoder.embed_utterance(speaker_wav)
        similarities = []
    
    # we will loop through the silences and try to find silences smaller than args.max_duration seconds and bigger than one second greedily by trying to cut on the biggest silences. Thus we will skip the first and last audio sample but we don't care
    sent_index, i, lost_seconds = 0, 0, 0
    to_save = []  # (audio, file_name)
    prog_bar = tqdm(total=len(silences))
    while i < len(silences):
        start_period = silences[i][0] + args.min_duration
        end_period = silences[i][0] + args.max_duration
        j, last_med_silence, last_short_silence, last_long_silence = 1, None, None, None
        while i + j < len(silences) and silences[i+j][0] < start_period:
            j += 1
        while i + j < len(silences) and silences[i+j][0] < end_period:
            if silences[i+j][2] == 0:
                last_short_silence = j
            elif silences[i+j][2] == 1:
                last_med_silence = j
            else:
                last_long_silence = j
                break
            j += 1
        
        if last_long_silence is None:
            if last_med_silence is not None:
                j = last_med_silence
            elif last_short_silence is not None:
                j = last_short_silence
            else:
                if i+1 < len(silences):
                    lost_seconds += (silences[i+1][0]+silences[i+1][1])/2 - (silences[i][0]+silences[i][1])/2
                i += 1
                prog_bar.update(i)
                continue
        
        sent_start = (silences[i][0] + silences[i][1]) / 2  # 50% of silence duration as a margin for safety, sec to ms
        sent_end = (silences[i+j][0] + silences[i+j][1]) / 2
            
        if args.remove_bad_segments:
            sent_wav = wav[int(sent_start * sampling_rate):int(sent_end * sampling_rate)]
            sent_embed = encoder.embed_utterance(sent_wav, rate=16)
            similarities.append(sent_embed @ speaker_embed)
            
        to_save.append((full_audio[sent_start*1000:sent_end*1000], f"sentence_{sent_index}.wav"))
        i += j
        sent_index += 1
        prog_bar.update(j)
    prog_bar.close()
    print(f"{lost_seconds : .2f} seconds of audio were cutted")
    
    # selects the similarity threshold at which we will remove audio
    if args.remove_bad_segments:
        print("Find a separation threshold on the histogram between speeches spoken by your speaker (closer to 1) and others (closer to 0). Then close the figure")
        plt.hist(similarities, bins=50)
        plt.title("histogram of the similarities (the higher the better)")
        plt.show()
        thr = -1
        
        while thr < 0 or thr > 1:
            str_thr = input("Please enter a valid threshold\n") 
            try:
                thr = float(str_thr)
            except ValueError as e:
                print("Value provided was not a float!")
    
    # saves the files
    csv_file = {"file": []}
    for i, (audio, file_name) in enumerate(to_save):
        if args.remove_bad_segments and similarities[i] < thr:
            continue
        csv_file["file"].append(file_name)
        audio.export(os.path.join(args.audio_folder, file_name), format="wav", parameters=params_list)
    
    csv_file["sentence"] = [""] * len(csv_file["file"])  # adding an empty column
    pd.DataFrame(csv_file).to_csv(args.out_csv, sep=";", index=False)
