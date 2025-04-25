__author__ = 'Prudhvi PLN'
__author__ = 'PanguPlay'

import sys
import os
import argparse
import time
import glob
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Utils.commons import load_yaml
from Clients.KissKhClient import KissKhClient
from Downloaders.HLSDownloader import HLSDownloader
from Downloaders.BaseDownloader import BaseDownloader

def try_import_msvcrt():
    """Try to import msvcrt module for Windows, return False if not available"""
    try:
        import msvcrt
        return msvcrt
    except ImportError:
        return False

def main():
    parser = argparse.ArgumentParser(description="Universal Downloader Bot (UDB) CLI for kisskh.ovh")

    parser.add_argument('search', nargs='?', type=str, help='Search keyword (e.g., "My Lovely Liar")')
    parser.add_argument('-i', '--index', type=int, help='Select series index from search results', default=1)
    parser.add_argument('-f','--start', type=int, default=1, help='Start episode number')
    parser.add_argument('-l','--end', type=int, default=None, help='End episode number')
    parser.add_argument('--specific', type=str, help='Comma-separated episode numbers (e.g., "1,5,10")')
    parser.add_argument('-r', '--resolution', default='720', help='Preferred resolution (e.g., 720, 1080)')
    parser.add_argument('--config', default='config_udb.yaml', help='Path to config YAML')
    parser.add_argument('-p','--profile', default='Drama (Asianbxkiun)', help='Profile name from config')
    parser.add_argument('-d','--download', action='store_true', default='-d', help='Start download after link fetch')
    parser.add_argument('-id', '--drama-id', type=int, help='Direct drama ID from kisskh.ovh site')

    args = parser.parse_args()
    
    if not args.search and not args.drama_id:
        print("❌ You must provide a search keyword or drama ID.")
        print('Ex 1 : python cli_udb.py "True Beauty" -f 1 -l 1')
        print('Ex 2 : python cli_udb.py -id 9507 -f 1 -l 1')
        sys.exit(1)

    config_all = load_yaml(args.config)
    config = config_all.get(args.profile)
    dl_config = config_all.get("DownloaderConfig", {})

    if not config:
        print(f"[ERROR] Config profile '{args.profile}' not found.")
        sys.exit(1)

    client = KissKhClient(config)

    if args.drama_id:
        target = client.fetch_drama_by_id(args.drama_id)
        if not target:
            print(f"[ERROR] Could not fetch drama by ID: {args.drama_id}")
            sys.exit(1)
        print(f"[INFO] Loaded drama by ID: {target.get('title', 'Unknown')}")
        target['series_type'] = target.get('type', 'tv')  # Normalize key for internal use
    else:
        print(f"🔍 Searching for: {args.search}")
        results = client.search(args.search)

        # Try exact match
        target = None
        for idx, item in results.items():
            if item['title'].strip().lower() == args.search.strip().lower():
                target = item
                print(f"[AUTO-MATCH] Found exact title match at index {idx}: {item['title']}")
                
                # Check if msvcrt is available (Windows)
                msvcrt = try_import_msvcrt()
                if msvcrt:
                    print("🕒 Press ESC to cancel auto-selection in the next 3 seconds...", end='', flush=True)
                    for i in range(30):
                        if msvcrt.kbhit() and msvcrt.getch() == b'\x1b':
                            print("\n❌ Auto-selection canceled.")
                            try:
                                user_index = int(input("👉 Enter the correct index manually: "))
                                target = results.get(user_index)
                            except:
                                print("[ERROR] Invalid input. Exiting.")
                                sys.exit(1)
                            break
                        time.sleep(0.1)
                    else:
                        print(" ✅ Auto-selection confirmed.")
                else:
                    # Non-Windows platforms
                    print("🕒 Auto-selecting in 3 seconds... (ESC not available)")
                    time.sleep(3)
                    print("✅ Auto-selection confirmed.")
                break

        if not target:
            if args.index not in results:
                print(f"[ERROR] Index {args.index} not in results.")
                sys.exit(1)
            target = results[args.index]
            print(f"[INDEX-MATCH] Using result from index {args.index}: {target['title']}")

    # Create drama-specific folder structure
    drama_title_safe = target['title'].replace(" ", "_").replace(":", "-").replace("/", "_").replace("\\", "_")
    base_download_dir = dl_config['download_dir']
    drama_dir = os.path.join(base_download_dir, drama_title_safe)
    temp_dir = os.path.join(drama_dir, "temp_dir")
    
    # Create directories
    os.makedirs(drama_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Important: Create a copy of the config to avoid modifying the original
    dl_config_copy = dl_config.copy()
    
    # Override temp_download_dir to use our temp_dir inside drama folder
    dl_config_copy['temp_download_dir'] = temp_dir
    
    episodes = client.fetch_episodes_list(target)
    end_ep = args.end if args.end else episodes[-1].get('episode')
    client.show_episode_results(episodes, args.start, end_ep)

    ep_range = {
        'start': args.start,
        'end': end_ep,
        'specific_no': list(map(int, args.specific.split(','))) if args.specific else []
    }

    download_links = client.fetch_episode_links(episodes, ep_range)
    client.fetch_m3u8_links(download_links, args.resolution, episode_prefix='Episode')

    try:
        if args.download:
            # When creating downloaders in main():
            for ep_id, data in client._get_udb_dict().items():
                # Check if episode already exists in the drama directory
                existing_episode = os.path.join(drama_dir, f"{data['episodeName']}.mp4")
                if os.path.exists(existing_episode):
                    print(f"⏩ Skipping existing episode: {data['episodeName']}")
                    continue
    
                # IMPORTANT: Set both out_dir and file_path correctly
                # This ensures files end up in the drama directory
                data['file_path'] = os.path.join(drama_dir, f"{data['episodeName']}.mp4")
    
                # Make sure the config points to the right drama directory
                # This is critical for the downloader classes
                temp_config = dl_config_copy.copy()
                temp_config['download_dir'] = drama_dir  # Set the download dir to drama directory
    
                # Create downloader with our custom config 
                if data['downloadType'] == 'hls':
                    downloader = HLSDownloader(temp_config, data)
                else:
                    downloader = BaseDownloader(temp_config, data)
    
                # Start download
                downloader.start_download(data['downloadLink'])
                
    except KeyboardInterrupt:
        print("\n⛔ Download interrupted by user (CTRL+C).")
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
    finally:
        print("🙏 Thanks for using Support Bot for UDB!")

if __name__ == '__main__':
    main()
