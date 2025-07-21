import os
import sys
import subprocess
import errno

# Change these paths as needed
input_folder = r"D:\inpath"
output_folder = r"D:\outpath"
FFMPEG_PATH = r"D:\Software\ffmpeg-7.1.1-full_build-shared\bin\ffmpeg.exe"

# Audacity pipe
if sys.platform == 'win32':
    print("running on windows")
    PIPE_TO = r"\\.\pipe\ToSrvPipe"
    PIPE_FROM = r"\\.\pipe\FromSrvPipe"
    EOL = '\r\n\0'
else:
    print("running on linux or mac")
    PIPE_TO = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
    PIPE_FROM = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
    EOL = '\n'

class AudacityPipe:
    def __init__(self):
        try:
            self.to_pipe = open(PIPE_TO, 'w', encoding='utf-8', buffering=1)
            self.from_pipe = open(PIPE_FROM, 'r', encoding='utf-8')
            print("-- Both pipes exist.  Good.")
        except OSError as e:
            if e.errno == errno.EINVAL:
                print("Windows named pipes can only be opened ONCE!!! restart Audacity and retry", file=sys.stderr)
            else:
                print(e, file=sys.stderr)
            exit()

    def send(self, command):
        self.to_pipe.write(command + EOL)
        self.to_pipe.flush()

    def read_response(self):
        result = ''
        line = ''
        while True:
            result += line
            line = self.from_pipe.readline()
            if line == '\n' and len(result) > 0:
                break
        return result

    def command(self, cmd):
        self.send(cmd)
        return self.read_response()

    def close(self):
        self.to_pipe.close()
        self.from_pipe.close()

def normalize_file(aud, file_path, output_path):
    file_path = file_path.replace("\\", "/")
    output_path = output_path.replace("\\", "/")
    print(f"🎵 Normalizing: {os.path.basename(file_path)}")

    aud.command(f'Import2: Filename="{file_path}"')
    aud.command('SelectAll:')
    aud.command("LoudnessNormalization: NormalizeType='LUFS' LoudnessTarget=-16 TruePeakLimit=-1.0")
    aud.command(f'Export2: Filename="{output_path}" NumChannels=1')
    aud.command('RemoveTracks:')

    print(f"Done: {os.path.basename(file_path)}")

def copy_album_art(original_path, normalized_path, ffmpeg_path=FFMPEG_PATH):
    temp_path = normalized_path + ".tmp.mp3"
    cmd = [
        ffmpeg_path,
        "-i", normalized_path,
        "-i", original_path,
        "-map", "0:a",
        "-map", "1:v?",
        "-c", "copy",
        "-id3v2_version", "3",
        temp_path
    ]
    subprocess.run(cmd, check=True)
    os.replace(temp_path, normalized_path)

# detailed export option settings are always stored to and taken from saved preferences
def main():
    os.makedirs(output_folder, exist_ok=True)
    aud = AudacityPipe()

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".mp3"):
            try:
                in_path = os.path.join(input_folder, filename)
                out_path = os.path.join(output_folder, filename)
                normalize_file(aud, in_path, out_path)
                copy_album_art(in_path, out_path)
            except Exception as e:
                print(f"Error with {filename}: {e}")

    aud.close()
    print("All files processed.")


if __name__ == "__main__":
    main()
