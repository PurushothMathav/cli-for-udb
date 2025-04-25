# 🎬 Support Bot using (UDB) - KissKH Edition

This version of UDB is a powerful, modular video downloader CLI tool tailored for scraping and downloading Asian dramas and anime from [kisskh.ovh](https://kisskh.ovh). It supports episode batch downloads, multiple subtitle tracks, and configurable profiles for different content types.

---

## 🚀 Features

- 🔍 Search or use direct drama ID to fetch series
- 🎯 Exact match auto-selection (with ESC to cancel)
- 📥 Batch or specific episode download (supports ranges or specific list)
- 📺 Auto-structured folders based on drama title and season
- 🧠 Smart resolution selector (lowest/highest/absolute)
- 🎞 Subtitle handling with language detection and renaming
- 💾 Temporary download directories with auto-cleanup
- ⚙ Configurable profiles via `config_udb.yaml`

---

## 📦 Requirements

Install the required dependencies:

```bash
pip install -r requirements.txt
```

**Dependencies include**:
- `requests`
- `beautifulsoup4`
- `pyyaml`
- `tqdm`
- `pycryptodomex`
- `undetected-chromedriver`
- `quickjs`
- `setuptools`

---

## 🛠 Configuration

Modify `config_udb.yaml` to define download folders, preferences, and client profiles.

### Example Profile (Drama):
```yaml
Drama (Asianbxkiun):
  request_timeout: 30
  alternate_resolution_selector: 'lowest'
  preferred_urls: []
  blacklist_urls: []

DownloaderConfig:
  download_dir: D:\kisskh dl\Videos
  temp_download_dir: auto
  concurrency_per_file: auto
  request_timeout: 30
  max_parallel_downloads: 2
```

---

## 💻 Usage

Run the script with either a search keyword or a direct drama ID.

### Search By Drama Name:
```bash
python cli_udb.py "True Beauty" -f 1 -l 4
```

### Search By Drama ID:
```bash
python cli_udb.py -id 9507 -f 1 -l 10
```

### Options:

| Flag                 | Description |
|----------------------|-------------|
| `search`             | Keyword to search (e.g. `"My Lovely Liar"`) |
| `-id`, `--drama-id`  | Direct drama ID |
| `-i`, `--index`      | Select from search results (default: 1) |
| `-f`, `--start`      | Start episode number |
| `-l`, `--end`        | End episode number |
| `--specific`         | Comma-separated list of episodes (e.g., `1,5,10`) |
| `-r`, `--resolution` | Preferred resolution (default: `720`) |
| `-d`, `--download`   | Start download after link fetch |
| `-p`, `--profile`    | Use config profile (default: `Drama (Asianbxkiun)`) |
| `--config`           | YAML config file (default: `config_udb.yaml`) |

---

## 📁 Output Structure

Each drama will be saved under:
```
<download_dir>/<Drama_Title>/[Season-X]/Episode-N.mp4
                            └── Episode-N.en.srt, .ko.srt, ...
```

---

## 🧪 Subtitle Handling

Subtitles are:
- Downloaded in parallel with video
- Renamed using language codes
- Stored alongside the episode

Auto-detection supports languages such as English, Korean, Spanish, French, etc.

---

## 📌 Notes

- `ffmpeg` is required and must be in your system path for HLS merging.
- Only `http.client` is used internally for some requests due to current site restrictions.

---

## 👨‍💻 Author

- Developed by **Prudhvi PLN**
- Modified by **PanguPlay**

---

## 🏷 License

This project is for educational purposes only.
