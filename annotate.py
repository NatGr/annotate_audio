import argparse
import pandas as pd
from tkinter import *
from tkinter import ttk
from tkinter import scrolledtext
import os
from pydub import AudioSegment
from pydub.playback import play
import threading
import logging
from datetime import datetime


class PlayAudioSample(threading.Thread):
    """plays the sound corresponding to an audio sample in its own thread"""
    def __init__(self, file_name):
        super().__init__()
        self.file_name = file_name
    
    def run(self):
        sound = AudioSegment.from_wav(self.file_name)
        play(sound)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser("""manually completes the transcriptions of audio files""")
    parser.add_argument("--audio_folder", help="folder that contains the audio files", required=True)
    parser.add_argument("--csv", help="name of the csv file that is to be filled with the files transcriptions", required=True)
    parser.add_argument("--start_offset", help="offset of the first file to consider", default=0, type=int)
    args = parser.parse_args()
    
    logdir = "logs"
    if not os.path.isdir(logdir):
        os.mkdir(logdir)
    logging.basicConfig(filename=os.path.join(logdir, f'{args.csv}_{str(datetime.now()).replace(" ", "_")}.log'), level=logging.DEBUG)

    
    files = pd.read_csv(args.csv, sep=";")
    offsets_deleted_sentences = []
    window = Tk()
    window.title(f"Transcription of {args.csv}")
    WIN_SIZE = 1200
    window.geometry(f'{WIN_SIZE}x500')
    
    instructions = Label(window, text="Audio files will be played automatically, transcribe them in the text area, then press ctrl-n to get to the next sample, ctrl-d to delete the current sample or ctrl-r to repeat the sample")
    instructions.grid(row=0, columnspan=3)
    
    transcription = scrolledtext.ScrolledText(window, width=130, height=20)
    transcription.grid(row=1, columnspan=3, pady=30)
    
    def prepare_next_turn():
        """loads next file or ends the program"""
        global current_offset, audio_player
        current_offset += 1
        progress_bar["value"] = current_offset
        if current_offset < len(files):
            transcription.delete("1.0", END)
            sent = files.sentence.iat[current_offset]
            if isinstance(sent, str) and sent != "":
                transcription.insert("1.0", sent)
            audio_player = PlayAudioSample(os.path.join(args.audio_folder, files.file.iat[current_offset])).start()
            transcription.focus()
        else:
            window.destroy()
    
    def press_next():
        """modifies csv with text content and prepares for next turn"""
        files.iat[current_offset, 1] = transcription.get("1.0", END).replace("\n", "")
        logging.info(f"{current_offset} - {files.iat[current_offset, 1]}")
        prepare_next_turn()
        
    def press_delete():
        """adds current phrase offset to instance of deleted phrases and prepares for next turns"""
        offsets_deleted_sentences.append(current_offset)
        logging.info(f"{current_offset} deleted")
        prepare_next_turn()
        
    def press_repeat():
        """repeats the previous audio file"""
        PlayAudioSample(os.path.join(args.audio_folder, files.file.iat[current_offset])).start()
        
    button_delete = Button(window, text="Delete", command=press_delete, bg="red")
    button_delete.grid(row=2, column=0)
    button_repeat = Button(window, text="Repeat", command=press_repeat, bg="blue")
    button_repeat.grid(row=2, column=1)
    button_next = Button(window, text="Next", command=press_next, bg="green")
    button_next.grid(row=2, column=2)
    window.bind('<Control-d>', lambda _: press_delete())
    window.bind('<Control-r>', lambda _: press_repeat())
    window.bind('<Control-n>', lambda _: press_next())
    
    progress_bar = ttk.Progressbar(window, style='blue.Horizontal.TProgressbar', length=WIN_SIZE, maximum=len(files))
    progress_bar.grid(row=4, columnspan=3)
    window.grid_rowconfigure(3, weight=1)  # so that pbar is at the bottom
    
    current_offset = args.start_offset - 1  # will be incremented by prepare_next_turn
    prepare_next_turn()
    window.mainloop()
    
    # deletes wav files to delete
    for i in offsets_deleted_sentences:
        file_name = os.path.join(args.audio_folder, files.file.iat[i])
        os.remove(file_name)
        print(f"{file_name} was deleted")
        
    index_to_keep = [i for i in range(len(files)) if i not in set(offsets_deleted_sentences)]
    files = files.iloc[index_to_keep]
    
    # save modified csv
    print("Save modified csv file")
    files.to_csv(args.csv, sep=";", index=False)