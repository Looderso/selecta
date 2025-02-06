import wave

import numpy as np


def create_dummy_mp3(filepath: str, artist: str, title: str) -> None:
    """Create a silent WAV file and convert to MP3 using ffmpeg."""
    # Create 1 second of silence
    samplerate = 44100
    samples = np.zeros(samplerate)

    # Save as WAV first
    wav_path = filepath.replace(".mp3", ".wav")
    with wave.open(wav_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(samplerate)
        wav_file.writeframes(samples.astype(np.int16).tobytes())

    # Convert to MP3 using ffmpeg
    import subprocess

    subprocess.run(["ffmpeg", "-i", wav_path, filepath, "-y", "-loglevel", "quiet"])
    import os

    os.remove(wav_path)

    # Add metadata
    audio = EasyID3(filepath)
    audio["artist"] = artist
    audio["title"] = title
    audio.save()
