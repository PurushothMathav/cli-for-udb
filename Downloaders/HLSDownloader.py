__author__ = 'Prudhvi PLN'

import os
import re
import shutil

from Utils.commons import retry
from Utils.BaseDownloader import BaseDownloader


class HLSDownloader(BaseDownloader):
    '''Download Client for HLS files'''
    # References: https://github.com/Oshan96/monkey-dl/blob/master/anime_downloader/util/hls_downloader.py
    # https://github.com/josephcappadona/m3u8downloader/blob/master/m3u8downloader/m3u8.py

    def __init__(self, dl_config, ep_details, session=None):
        # initialize base downloader
        super().__init__(dl_config, ep_details, session)
        # initialize HLS specific configuration
        self.m3u8_file = os.path.join(f'{self.temp_dir}', 'uwu.m3u8')
        self.thread_name_prefix = 'udb-hls-'

    def _has_uri(self, m3u8_data):
        method = re.search('URI=(.*)', m3u8_data)
        if method is None: return False
        if method.group(1) == "NONE": return False

        return True

    def _collect_uri_iv(self, m3u8_data):
        # Case-1: typical HLS using URI & IV
        uri_iv = re.search('#EXT-X-KEY:METHOD=AES-128,URI="(.*)",IV=(.*)', m3u8_data)

        # Case-2: typical HLS using URI only
        if uri_iv is None:
            uri_data = re.search('URI="(.*)"', m3u8_data)
            return uri_data.group(1), None

        uri = uri_iv.group(1)
        iv = uri_iv.group(2)

        return uri, iv

    def _collect_ts_urls(self, m3u8_link, m3u8_data):
        # Improved regex to handle all cases. (get all lines except those starting with #)
        base_url = '/'.join(m3u8_link.split('/')[:-1])
        normalize_url = lambda url, base_url: (url if url.startswith('http') else 'https:' + url if url.startswith('//') else base_url + '/' + url)
        # Some m3u8 files have duplicate urls, so using set to remove duplicates
        urls = list(set( normalize_url(url.group(0), base_url) for url in re.finditer("^(?!#).+$", m3u8_data, re.MULTILINE) ))

        return urls

    @retry()
    def _download_segment(self, ts_url):
        '''
        download segment file from url. Reuse if already downloaded.

        Returns: (download_status, progress_bar_increment)
        '''
        try:
            segment_file_nm = ts_url.split('/')[-1]
            segment_file = os.path.join(f"{self.temp_dir}", f"{segment_file_nm}")

            # check if the segment is already downloaded
            if os.path.isfile(segment_file) and os.path.getsize(segment_file) > 0:
                return (f'Segment file [{segment_file_nm}] already exists. Reusing.', 1)

            with open(segment_file, "wb") as ts_file:
                ts_file.write(self._get_stream_data(ts_url))

            return (f'Segment file [{segment_file_nm}] downloaded', 1)

        except Exception as e:
            return (f'\nERROR: Segment download failed [{segment_file_nm}] due to: {e}', 0)

    def _rewrite_m3u8_file(self, m3u8_data):
        # regex safe temp dir path
        seg_temp_dir = self.temp_dir.replace('\\', '\\\\')
        # ffmpeg doesn't accept backward slash in key file irrespective of platform
        key_temp_dir = self.temp_dir.replace('\\', '/')
        with open(self.m3u8_file, 'w', encoding='utf-8') as m3u8_f:
            m3u8_content = re.sub('URI=(.*)/', f'URI="{key_temp_dir}/', m3u8_data, count=1)
            regex_safe = '\\\\' if os.sep == '\\' else '/'
            # strip off url for segments
            m3u8_content = re.sub(r'(.*)//(.*)/', '', m3u8_content)
            # prefix the downloaded path for segments
            m3u8_content = re.sub(r'^(?!#).+$', rf'{seg_temp_dir}{regex_safe}\g<0>', m3u8_content, flags=re.MULTILINE)
            m3u8_f.write(m3u8_content)

    def _convert_to_mp4(self):
        # print(f'Converting {self.out_file} to mp4')
        out_file = os.path.join(f'{self.out_dir}', f'{self.out_file}')
        command = [f'ffmpeg -loglevel warning -allowed_extensions ALL -i "{self.m3u8_file}"']
        maps = ['-map 0:v -map 0:a'] if self.subtitles else []
        metadata = []

        # Prepare the command if subtitles are present
        for i, (lang, url) in enumerate(self.subtitles.items(), start=1):
            command.append(f'-i "{url}"')
            maps.append(f'-map {i}')
            metadata.append(f'-metadata:s:s:{i-1} title="{lang}"')

        metadata.append(f'-c:v copy -c:a copy -c:s mov_text -bsf:a aac_adtstoasc "{out_file}"')

        cmd = ' '.join(command + maps + metadata)
        self._exec_cmd(cmd)
    
    def _move_file(self, src, dest):
        """Helper method to move files with proper error handling"""
        try:
            shutil.copy2(src, dest)
            self.logger.debug(f"Moved file from {src} to {dest}")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to move file from {src} to {dest}: {e}")
            return False

    def _remove_out_dirs(self):
        """Process subtitle files, move them to output directory, and clean up temp directory"""
        # Extract the base episode name without extension
        episode_base_name = os.path.splitext(self.out_file)[0]
    
        # Make sure output directory exists
        os.makedirs(self.out_dir, exist_ok=True)
    
        # Keep track of processed files to ensure we don't delete needed files
        processed_files = []
    
        # Language code mapping (add more as needed)
        language_mappings = {
            'arabic': 'ar',
            'english': 'en',
            'hindi': 'hi',
            'indonesia': 'id',
            'khmer': 'km',
            'malay': 'ms',
            'spanish': 'es',
            'french': 'fr',
            'german': 'de',
            'italian': 'it',
            'japanese': 'ja',
            'korean': 'ko',
            'chinese': 'zh',
            'russian': 'ru',
            'vietnamese': 'vi',
            'thai': 'th',
            'portuguese': 'pt',
            'turkish': 'tr',
        }
    
        # Process subtitle files first - rename and move to output directory
        subtitle_count = 0
        for root, dirs, files in os.walk(self.temp_dir):
            for file in files:
                if file.endswith('.srt'):
                    try:
                        # Get original file path
                        original_path = os.path.join(root, file)
                    
                        # Determine language code from filename
                        lang_code = None
                        file_lower = file.lower()
                    
                        # First, try to find from standard language codes in filename
                        lang_code_match = re.search(r'\.([a-z]{2})\.srt$', file_lower)
                        if lang_code_match:
                            lang_code = lang_code_match.group(1)
                        else:
                            # Try to find from file prefix
                            file_prefix = file_lower.split('_')[0]
                            if file_prefix in language_mappings:
                                lang_code = language_mappings[file_prefix]
                            # Check for language names in the filename
                            else:
                                for lang_name, code in language_mappings.items():
                                    if lang_name.lower() in file_lower:
                                        lang_code = code
                                        break
                    
                        # Default to English if language can't be determined
                        if not lang_code:
                            self.logger.debug(f"Could not determine language code for {file}, defaulting to English")
                            lang_code = 'en'
                    
                        # Create new filename with episode name and language code
                        new_filename = f"{episode_base_name}.{lang_code}.srt"
                        new_path = os.path.join(self.out_dir, new_filename)
                    
                        # Move and rename file using our helper method
                        self._move_file(original_path, new_path)
                        processed_files.append(original_path)
                        subtitle_count += 1
                        self.logger.debug(f"Processed subtitle: {file} → {new_filename}")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to process subtitle file {file}: {e}")
    
        # Also ensure video file is in output directory if it exists in temp
        mp4_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.mp4')]
        for mp4_file in mp4_files:
            try:
                src_path = os.path.join(self.temp_dir, mp4_file)
                dest_path = os.path.join(self.out_dir, mp4_file)
                if os.path.exists(src_path) and not os.path.exists(dest_path):
                    self._move_file(src_path, dest_path)
                    processed_files.append(src_path)
                    self.logger.debug(f"Moved video file: {mp4_file} to {self.out_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to move video file {mp4_file}: {e}")
    
        self.logger.debug(f"Processed {subtitle_count} subtitle files")
    
        # Now clean up temp directory - remove processed files first
        for file_path in processed_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                self.logger.warning(f"Failed to remove processed file {file_path}: {e}")
    
        # Remove any remaining files in temp_dir
        try:
            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        except Exception as e:
            self.logger.warning(f"Error cleaning remaining files in temp dir: {e}")
    
        # Now remove the temp directory itself
        try:
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)
                self.logger.debug("Removed temp_dir after moving files.")
        except Exception as e:
            self.logger.warning(f"Failed to remove temp_dir: {e}")
    
        # Check if parent temp dir is empty and remove if it is
        try:
            if os.path.exists(self.parent_temp_dir) and len(os.listdir(self.parent_temp_dir)) == 0:
                os.rmdir(self.parent_temp_dir)
                self.logger.debug("Removed parent temp_dir (empty).")
        except Exception as e:
            self.logger.warning(f"Failed to remove parent temp_dir: {e}")

    def start_download(self, m3u8_link):
        # create output directory
        self._create_out_dirs()

        iv = None
        self.logger.debug('Fetching stream data')
        m3u8_data = self._get_stream_data(m3u8_link, True)

        self.logger.debug('Check if stream is encrypted/mapped')
        if self._has_uri(m3u8_data):
            self.logger.debug('Stream is encrypted/mapped. Collect iv data and download key')
            key_uri, iv = self._collect_uri_iv(m3u8_data)
            status = self._download_segment(key_uri)
            if status[1] == 0: self.logger.error(f'Failed to download key/map file with error: {status[0]}')

        # did not run into HLS with IV during development, so skipping it
        if iv:
            raise Exception("Current code cannot decode IV links")

        self.logger.debug('Collect m3u8 segment urls')
        ts_urls = self._collect_ts_urls(m3u8_link, m3u8_data)

        self.logger.debug('Downloading collected segments')
        metadata = {
            'type': 'segments',
            'total': len(ts_urls),
            'unit': 'seg'
        }
        self._multi_threaded_download(self._download_segment, ts_urls, **metadata)

        self.logger.debug('Rewrite m3u8 file with downloaded segments paths')
        self._rewrite_m3u8_file(m3u8_data)

        if self.subtitles:
            self.logger.debug('Downloading subtitles')
            self._download_subtitles()

        self.logger.debug('Converting m3u8 segments to .mp4')
        self.logger.debug('Starting mp4 conversion')
        self._convert_to_mp4()
        self.logger.debug('Completed mp4 conversion')

        # Remove temp dir once completed
        self.logger.debug('Removing temporary directories')
        self._remove_out_dirs()

        return (0, None)