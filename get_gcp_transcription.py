from google.cloud import speech_v1
import io
import argparse
import pandas as pd
import os
from tqdm import tqdm


if __name__ == "__main__":
    parser = argparse.ArgumentParser("""Uses GCP to transcribe short audio files""")
    parser.add_argument("--audio_folder", help="folder that contains the audio files", required=True)
    parser.add_argument("--language_code", help="speaker language code", required=True)  # en-US or fr-FR for example
    parser.add_argument(
        "--csv", help="name of the csv file that is to be filled with the files transcript transcript", required=True)
    args = parser.parse_args()

    files = pd.read_csv(args.csv, sep=";", dtype="string")
    config = {
        "language_code": args.language_code,
        "use_enhanced": True,
        "enable_automatic_punctuation": True,
    }
        
    client = speech_v1.SpeechClient()
    
    for i in tqdm(range(len(files)), desc="files transcribed"):
        file_name = os.path.join(args.audio_folder, files.iat[i, 0])
        with io.open(file_name, "rb") as f:
            content = f.read()
        audio = {"content": content}
        response = client.recognize(config, audio)
        transcript = ' '.join([result.alternatives[0].transcript for result in response.results])
        files.iat[i, 1] = transcript
        
    # writes transcripts to file
    files.to_csv(args.csv, sep=";", index=False)
