import os
import subprocess
import json

# Define the rename mapping
RENAME_MAP = {
    0: 'en',
    1: 'id',
    2: 'ms',
    3: 'ar',
    4: 'km',
    5: 'hi',
}

def get_subtitle_streams(file_path):
    """Get all subtitle streams info."""
    cmd = [
        'ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams',
        '-select_streams', 's', file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    return info.get('streams', [])

def sanitize(name):
    """Sanitize filename."""
    return name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')

def extract_all_subtitles(video_file):
    """Extract all subtitles without relying on metadata."""
    base_name = os.path.splitext(video_file)[0]
    streams = get_subtitle_streams(video_file)

    if not streams:
        print(f"No subtitles found in {video_file}")
        return

    for i, stream in enumerate(streams):
        output_srt = f"{base_name}.sub{i}.srt"

        if os.path.exists(output_srt):
            print(f"Already exists, skipping: {output_srt}")
            continue

        print(f"Extracting subtitle: {output_srt}")
        cmd = [
            'ffmpeg', '-y', '-i', video_file, '-map', f'0:s:{i}',
            output_srt
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Rename after all extraction
    for i, lang_code in RENAME_MAP.items():
        old_srt = f"{base_name}.sub{i}.srt"
        new_srt = f"{base_name}.{lang_code}.srt"
        if os.path.exists(old_srt):
            print(f"Renaming {old_srt} -> {new_srt}")
            os.rename(old_srt, new_srt)

def main():
    folder = os.getcwd()

    for file in os.listdir(folder):
        if file.lower().endswith('.mp4'):
            print(f"\nProcessing: {file}")
            extract_all_subtitles(file)

if __name__ == "__main__":
    main()
