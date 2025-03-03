import os
import re
import shutil
import subprocess
import ffmpeg
import json
import sys
import pytubefix.extract
from pytubefix import YouTube, Channel
from pytubefix.cli import on_progress


version = 0.6


class BCOLORS:
    CYAN       = "\033[96m"
    MAGENTA    = "\033[95m"
    BLUE       = "\033[94m"
    YELLOW     = "\033[93m"
    GREEN      = "\033[92m"
    RED        = "\033[91m"
    BLACK      = "\033[90m"
    ORANGE     = "\033[33m"
    UNDERLINE  = "\033[4m"
    BOLD       = "\033[1m"
    ENDC       = "\033[0m"


REQUIRED_CONFIG = {
    "c_max_resolution": "",
    "c_ignore_min_duration": "",
    "c_ignore_max_duration": "",
    "c_only_restricted": "",
    "c_skip_restricted": "",
    "c_minimum_views": "",
    "c_exclude_video_ids": "",
    "c_include_video_ids": "",
    "c_filter_words": ""
}


def cc_load_config(file_path):
    """Loads the JSON config file or creates an empty dictionary if the file doesn't exist."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)  # Load existing config
            except json.JSONDecodeError:
                print("❌ Error: Invalid JSON format. Resetting to default config.")
                return {}  # Return an empty config if JSON is corrupted
    return {}  # Return an empty config if file doesn't exist

def cc_save_config(cc_file_path, cc_config):
    """Saves the updated config dictionary back to the JSON file."""
    with open(cc_file_path, "w", encoding="utf-8") as cc_file:
        json.dump(cc_config, cc_file, indent=4, ensure_ascii=False)
    #print(f"✅ Updated config saved to {cc_file_path}")

def cc_check_and_update_channel_config(cc_file_path, cc_required_config):
    """Ensures all required keys exist in the config file, adding missing ones."""
    cc_config = cc_load_config(cc_file_path)  # Load existing or empty config

    # Check for missing keys and add them
    missing_keys = []
    for key, default_value in cc_required_config.items():
        if key not in cc_config:
            cc_config[key] = default_value
            missing_keys.append(key)

    if missing_keys:
        #print(f"⚠️ Missing keys added: {', '.join(missing_keys)}")
        cc_save_config(cc_file_path, cc_config)  # Save only if changes were made
    # else:
    #     print("✅ All required config keys exist. No updates needed.")


def clear_screen():
    """Clears the console screen on Windows and Linux/macOS."""
    os.system('cls' if os.name == 'nt' else 'clear')


def load_config(c_file):
    """Load settings from config.json."""
    with open(c_file, "r") as file:
        l_config = json.load(file)
    return l_config


def print_asteriks_line():
    length = 84
    print("*" * length)


def print_configuration():
    print("CONFIGURATION (config.json):")
    print_asteriks_line()
    print(print_colored_text("Output directory:                   ", BCOLORS.BLACK),
          print_colored_text(output_dir, BCOLORS.CYAN))
    print(print_colored_text("Minimum Video Duration in Minutes:  ", BCOLORS.BLACK),
          print_colored_text(min_duration, BCOLORS.CYAN))
    print(print_colored_text("Maximum Video Duration in Minutes:  ", BCOLORS.BLACK),
          print_colored_text(max_duration, BCOLORS.CYAN))
    if year_subfolders:
        year_subfolders_colored = print_colored_text(year_subfolders, BCOLORS.GREEN)
    else:
        year_subfolders_colored = print_colored_text(year_subfolders, BCOLORS.RED)
    print(print_colored_text("Year Subfolder-Structure:           ", BCOLORS.BLACK),
          year_subfolders_colored)
    print_asteriks_line()
    print("")


def format_header(counter, width):
    # width = 95
    counter_splitted = counter.split(" - ")
    counter_str = ("* " + counter_splitted[0] + " *" + print_colored_text(f" {counter_splitted[1]} ", BCOLORS.CYAN)
                   + "| " + counter_splitted[2] + " (" + get_free_space(dlpath) + " free) ")
    total_length = width - 2  # Exclude parentheses ()

    # Center the counter with asterisks
    formatted = f"{counter_str.ljust(total_length, '*')}"

    return formatted


def print_video_infos(yt, res, video_views):
    print(print_colored_text("Title:         ", BCOLORS.BLACK),
          print_colored_text(print_colored_text(yt.title, BCOLORS.CYAN), BCOLORS.BOLD))
    if min_video_views_bool:
        print(print_colored_text("Views:         ", BCOLORS.BLACK),
              format_view_count(video_views), " (> " + format_view_count(min_video_views) + ")")
    else:
        print(print_colored_text("Views:         ", BCOLORS.BLACK),
              format_view_count(video_views))
    print(print_colored_text("Date:          ", BCOLORS.BLACK), yt.publish_date.strftime("%Y-%m-%d"))

    if ignore_max_duration_bool and ignore_min_duration_bool:
        print(print_colored_text("Length:        ", BCOLORS.BLACK), str(int(yt.length / 60)) + "m")
    elif ignore_max_duration_bool:
        print(print_colored_text("Length:        ", BCOLORS.BLACK),
              str(int(yt.length / 60)) + "m", " (" + min_duration + "m <")
    elif ignore_min_duration_bool:
        print(print_colored_text("Length:        ", BCOLORS.BLACK),
              str(int(yt.length / 60)) + "m", " (< " + max_duration + "m")
    else:
        print(print_colored_text("Length:        ", BCOLORS.BLACK),
              str(int(yt.length / 60)) + "m", " (" + min_duration + "m < " + max_duration + "m)")

    print(print_colored_text("Resolution:    ", BCOLORS.BLACK),
          print_colored_text(res, BCOLORS.YELLOW), " (" + limit_resolution_to + ")")
    print("               ", print_colored_text(print_resolutions(yt), BCOLORS.BLACK))


def print_colored_text(message_text, color):
    return f"{color}{message_text}{BCOLORS.ENDC}"


def get_free_space(path):
    """Returns the free disk space for the given path formatted in GB or MB."""
    total, used, free = shutil.disk_usage(path)  # Get disk space (in bytes)

    # Convert bytes to GB or MB for readability
    if free >= 1_000_000_000:  # If space is at least 1GB
        formatted_space = f"{free / 1_073_741_824:.1f} GB"
    else:
        formatted_space = f"{free / 1_048_576:.0f} MB"  # Otherwise, use MB

    return formatted_space


def clean_youtube_urls(toclean_video_list):
    """Removes 'https://www.youtube.com/watch?v=' from YouTube URLs in a list,
    keeping only the video ID.
    """
    prefix = youtube_base_url

    return [toclean_video.replace(prefix, "") for toclean_video in toclean_video_list]


def string_to_list(input_string):
    """Transforms a comma-separated string into a list of strings, removing extra spaces."""
    return [item.strip() for item in input_string.split(",")]


def format_view_count(number):
    """Formats a number into a human-readable view count."""
    if number >= 1_000_000_000:  # Billions
        return f"{number / 1_000_000_000:.1f}B"
    elif number >= 1_000_000:  # Millions
        return f"{number / 1_000_000:.1f}M"
    elif number >= 1_000:  # Thousands
        return f"{number / 1_000:.1f}K"
    else:
        return str(number)


def clean_string_regex(text):
    """
    Removes characters that do NOT match the given pattern.

    :param text: The input string to clean.
    :return: The cleaned string.
    """
    new_text = text.replace(":", "")

    pattern = r"[^a-zA-Z0-9 ]"

    return re.sub(pattern, "", new_text)


def rename_files_in_temp_directory():
    """Removes ':' from filenames in a given directory."""
    directory = os.getcwd()
    if not os.path.exists(directory):
        print("Error: Directory does not exist!")
        return

    for filename in os.listdir(directory):
        if ":" in filename:  # Check if filename contains ':'
            sanitized_name = filename.replace(":", "")
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, sanitized_name)

            os.rename(old_path, new_path)
            #print(f"Renamed: {filename} → {sanitized_name}")


def read_channel_txt_lines(filename):
    """Reads all lines from a file and returns a list of lines."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            rc_lines = [line.strip() for line in file.readlines()]  # Remove newlines
        rc_lines.append("--- Enter YouTube Channel or Video URL ---")
        return rc_lines
    except FileNotFoundError:
        print("❌ Error: File not found.")
        return []


def user_selection(u_lines):
    """Displays the lines as a selection menu and gets user input."""
    if not u_lines:
        print("No lines available for selection.")
        return None

    print("Select channel:")
    for index, line in enumerate(u_lines, start=1):
        print(f"{index}. {line}")

    while True:
        try:
            choice = int(input("\nEnter the number of your choice: "))
            if 1 <= choice <= len(u_lines):
                return u_lines[choice - 1]  # Return selected line
            else:
                print("⚠️ Invalid selection. Choose a valid number.")
        except ValueError:
            print("⚠️ Invalid input. Please enter a number.")


def delete_temp_files():
    # remove video and audio streams
    video_file, audio_file = find_media_files(".")
    # Check if files exist before deleting
    if video_file and os.path.exists(video_file):
        os.remove(video_file)

    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)


def smart_input(prompt, default_value):
    user_input = input(f"{prompt} [{default_value}]: ").strip()
    return user_input if user_input else default_value


def find_media_files(fmf_path):
    """Search for the first MP4 and M4A files in the current directory."""
    video_file = None
    audio_file = None

    for file in os.listdir(fmf_path):
        if file.endswith((".mp4", ".webm")) and video_file is None:
            video_file = file
        elif file.endswith(".m4a") and audio_file is None:
            audio_file = file

        if video_file and audio_file:
            break  # Stop searching once both files are found

    return video_file, audio_file


# def move_video_audio():
#     video_file, audio_file = find_media_files()
#     destination_video = dlpath + "/" + video_file  # Destination path
#     destination_audio = dlpath + "/" + audio_file  # Destination path
#
#     shutil.move(video_file, destination_video)
#     shutil.move(audio_file, destination_audio)
#
#     print(f"✅ Moved files to download path!")


def print_resolutions(yt):
    streams = yt.streams.filter(file_extension='mp4')  # StreamQuery object
    # Convert StreamQuery to a formatted string
    stream_string = "\n".join([str(stream) for stream in streams])
    # Extract resolutions using regex
    resolutions = re.findall(r'res="(\d+p)"', stream_string)
    # Remove duplicates and sort in descending order
    unique_resolutions = sorted(set(resolutions), key=lambda x: int(x[:-1]), reverse=True)

    return unique_resolutions


def find_file_by_string(directory, search_string, resolution):
    """Searches a directory for a file containing a specific string in its filename.

    Returns the filename if found, otherwise returns None.
    """
    if resolution=="max":
        resolution = ""

    if not os.path.exists(directory):
        #print("Error: Directory does not exist!")
        return None

    # Iterate over each file in the directory
    for root, _, files in os.walk(directory):  # os.walk() traverses all subdirectories
        for filename in files:
            if search_string in filename and resolution in filename:
                return os.path.join(root, filename)  # Return full file path of the first match

    return None  # Return None if no file is found


def limit_resolution(resolution, limit):
    num_resolution = int(''.join(filter(str.isdigit, resolution)))  # Extract number from first resolution
    if limit!="max":
        num_limit = int(''.join(filter(str.isdigit, limit)))  # Extract number from second resolution
    if str(limit)=="max" or num_resolution < num_limit:
        max_resolution = resolution
    else:
        max_resolution = limit

    return max_resolution


def download_video_restricted(videoid, counterid, video_total_count, channel_name, video_views):
    yt = YouTube(youtube_base_url + videoid, use_oauth=True, allow_oauth_cache=True, on_progress_callback = on_progress)

    print("\n")
    colored_video_id = print_colored_text(videoid, BCOLORS.RED)
    print(format_header(colored_video_id + " - " + channel_name
                        + " - " + str(counterid) + "/" + str(video_total_count), 104))

    publishing_date = yt.publish_date.strftime("%Y-%m-%d")
    if year_subfolders:
        year = yt.publish_date.strftime("%Y")
    else:
        year = ""

    res = max(print_resolutions(yt), key=lambda x: int(x.rstrip('p')))
    if limit_resolution_to != "max":
        res = limit_resolution(res, limit_resolution_to)

    print_video_infos(yt, res, video_views)

    if os.path.exists(
            dlpath + str(year) + "/restricted/" + str(publishing_date) + " - " + res + " - " + clean_string_regex(
                yt.title) + " - " + yt.video_id + ".mp4"):
        print(print_colored_text("\nVideo already downloaded", BCOLORS.GREEN))
    else:
        more_than1080p = 0

        # here check if /temp/file already exists

        if res == "2160p" or res == "1440p":
            more_than1080p = 1
            video_file_tmp, audio_file_tmp = find_media_files("tmp")
            if video_file_tmp!="None":
                restricted_string = "/restricted/"
                path = (dlpath + str(year) + restricted_string + str(publishing_date) + " - " + res + " - "
                        + clean_string_regex(os.path.splitext(video_file_tmp)[0]) + " - " + videoid + ".mp4")
                print(print_colored_text("Merged file already present.", BCOLORS.GREEN))
                print(f"Converting to MP4... (this may take a while)")
                convert_webm_to_mp4("tmp/" + video_file_tmp, path, True)
                question = input("Whats next... Continue? Y/n")
                if question == "n":
                    exit()

        print("\nDownloading VIDEO...")

        for idx, i in enumerate(yt.streams):
            if i.resolution == res:
                break
        yt.streams[idx].download()

        print("\nDownloading AUDIO...")

        for idx, i in enumerate(yt.streams):
            if i.bitrate == "128kbps":
                break
        yt.streams[idx].download()

        if not os.path.exists(dlpath + f"{year}/restricted"):
            os.makedirs(dlpath + f"{year}/restricted")

        rename_files_in_temp_directory()

        if more_than1080p == 0:
            print("\nMerging...")
            merge_video_audio(yt.video_id, publishing_date, res, year, True)
        else:
            print("\nMerging...")
            # move_video_audio()
            convert_m4a_to_opus_and_merge(yt.video_id, publishing_date, res, year, True)


def download_video(videoid, counterid, video_total_count, video_views):
    yt = YouTube(youtube_base_url + videoid, on_progress_callback=on_progress)

    print(format_header(videoid + " - " + yt.author + " - " + str(counterid) + "/" + str(video_total_count), 95))

    publishing_date = yt.publish_date.strftime("%Y-%m-%d")
    if year_subfolders:
        year = "/" + str(yt.publish_date.strftime("%Y"))
    else:
        year = ""

    res = max(print_resolutions(yt), key=lambda x: int(x.rstrip('p')))
    if limit_resolution_to != "max":
        res = limit_resolution(res, limit_resolution_to)

    print_video_infos(yt, res, video_views)

    # check if file was already downloaded
    if os.path.exists(dlpath + year + "/" + str(publishing_date) + " - " + res + " - " + clean_string_regex(yt.title) + " - "+ videoid + ".mp4"):
        print(print_colored_text("\nVideo already downloaded\n", BCOLORS.GREEN))
    else:
        more_than1080p = 0

        if res == "2160p" or res == "1440p":
            more_than1080p = 1

        print("\nDownloading VIDEO...")

        for idx, i in enumerate(yt.streams):
            if i.resolution == res:
                break
        yt.streams[idx].download()

        print("\nDownloading AUDIO...")

        for idx, i in enumerate(yt.streams):
            if i.bitrate == "128kbps":
                break
        yt.streams[idx].download()

        rename_files_in_temp_directory()

        print("\nMerging...")
        if more_than1080p == 0:
            merge_video_audio(videoid, str(publishing_date), res, year, False)
        else:
            convert_m4a_to_opus_and_merge(videoid, str(publishing_date), res, year, False)


def merge_video_audio(videoid, publishdate, video_resolution, year, restricted):
    video_file, audio_file = find_media_files(".")

    if not video_file or not audio_file:
        print("❌ No MP4 or M4A files found in the current directory.")
        return

    if not os.path.exists(dlpath + f"{str(year)}"):
        os.makedirs(dlpath + f"{str(year)}")

    if restricted:
        restricted_path = "/restricted/"
    else:
        restricted_path = "/"
    output_file = dlpath + str(year) + restricted_path + publishdate + " - " + video_resolution + " - " + clean_string_regex(os.path.splitext(video_file)[0]) + " - " + videoid + ".mp4"

    """Merge video and audio into a single MP4 file using FFmpeg."""
    try:
        #print(f"🎬 Merging Video: {video_file}")
        #print(f"🎵 Merging Audio: {audio_file}")

        # Input video and audio streams
        m_video = ffmpeg.input(video_file)
        audio = ffmpeg.input(audio_file)

        # Merge video and audio
        output = ffmpeg.output(m_video, audio, output_file, vcodec="copy", acodec="aac", strict="experimental")

        output = output.global_args("-stats")

        # Run FFmpeg command
        ffmpeg.run(output, overwrite_output=True, quiet=True)
        #print(f"\n✅ \033[92mMerged file saved as: {output_file}.\033[0m")
        if restricted:
            print(print_colored_text("\nRestricted Video downloaded", BCOLORS.GREEN))
        else:
            print(print_colored_text("\nVideo downloaded", BCOLORS.GREEN))
        # remove video and audio streams
        delete_temp_files()

    except Exception as ee:
        print(f"❌ Error merging files: {ee}")
        sys.exit(1)


def convert_m4a_to_opus_and_merge(videoid, publishdate, video_resolution, year, restricted):
    video_file, audio_file = find_media_files(".")
    """Convert M4A to Opus format (WebM-compatible)."""
    command = [
        "ffmpeg", "-loglevel", "quiet", "-stats", "-i", audio_file, "-c:a", "libopus", "audio.opus"
    ]
    subprocess.run(command, check=True)
    # print(f"✅ Converted {audio_file} to audio.opus")
    merge_webm_opus(videoid, publishdate, video_resolution, year, restricted)


def merge_webm_opus(videoid, publishdate, video_resolution, year, restricted):
    video_file, audio_file = find_media_files(".")
    output_file = "tmp/" + video_file
    """Merge WebM video with Opus audio."""
    command = [
        "ffmpeg", "-loglevel", "quiet", "-stats", "-i", video_file, "-i", "audio.opus",
        "-c:v", "copy", "-c:a", "copy", output_file
    ]
    subprocess.run(command, check=True)
    # remove video and audio streams
    delete_temp_files()
    os.remove("audio.opus")
    print(f"Converting to MP4... (this may take a while)")
    restricted_string = "/"
    if restricted:
        restricted_string = "/restricted/"

    path = (dlpath + str(year) + restricted_string + publishdate + " - " + video_resolution + " - "
            + clean_string_regex(os.path.splitext(video_file)[0]) + " - " + videoid + ".mp4")
    convert_webm_to_mp4(output_file, path, restricted)


def convert_webm_to_mp4(input_file, output_file, restricted):
    """Convert a WebM file to MP4 (H.264/AAC)."""
    command = [
        "ffmpeg", "-loglevel", "quiet", "-stats", "-i", input_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",  # H.264 video encoding
        "-c:a", "aac", "-b:a", "128k",  # AAC audio encoding
        "-movflags", "+faststart",  # Optimize MP4 for streaming
        output_file
    ]
    subprocess.run(command, check=True)
    os.remove(input_file)
    if restricted:
        print(print_colored_text("\nRestricted Video downloaded", BCOLORS.GREEN))
    else:
        print(print_colored_text("\nVideo downloaded", BCOLORS.GREEN))


while True:
    try:
        # Load config
        config = load_config("config.json")
        # Access settings
        output_dir = config["output_directory"]
        youtube_base_url = config["youtube_base_url"]
        min_duration = config["min_duration_in_minutes"]
        max_duration = config["max_duration_in_minutes"]
        year_subfolders = config["year_subfolders"]

        # Create an empty list
        video_list = []
        video_list_restricted = []

        clear_screen()
        print(print_colored_text("\nYTDL " + str(version), BCOLORS.YELLOW))
        print("********")
        print("YouTube Channel Downloader")
        print("Exit App with Ctrl + C")
        print(print_colored_text("https://github.com/SteveAustin79/YTDL\n", BCOLORS.BLACK))
        delete_temp_files()
        print_configuration()

        lines = read_channel_txt_lines("channels.txt")
        if lines and len(lines) > 1:
            YTchannel = user_selection(lines)
        else:
            YTchannel = input("\nYouTube Channel or Video URL:  ")
        if "- Enter YouTube Channel or Video URL -" in YTchannel:
            YTchannel = input("\nYouTube Channel or Video URL:  ")

        video_id_from_single_video = ""
        if youtube_base_url in YTchannel:
            ytv = YouTube(YTchannel, on_progress_callback=on_progress)
            YTchannel = ytv.channel_url
            video_id_from_single_video = ytv.video_id

        #count_fetch_videos = str(smart_input("Fetch x latest Videos (to download all playable/unrestricted videos use 'all'): ", "all"))
        #skip_x_videos = int(smart_input("Skip x videos: ", "0"))

        c = Channel(YTchannel)
        print("\n" + print_colored_text(str(YTchannel), BCOLORS.BOLD))
        print(print_colored_text("*" * len(str(YTchannel)), BCOLORS.BOLD))

        dlpath = smart_input("\nDownload Path:  ", output_dir + "/" + clean_string_regex(c.channel_name).rstrip())

        default_max_res = "max"
        default_ignore_min_duration = "y"
        default_ignore_max_duration = "y"
        default_only_restricted = "n"
        default_skip_restricted = "n"
        default_minimum_views = "0"
        default_exclude_videos = ""
        default_include_videos = ""
        default_filter_words = ""

        channel_config_path = "/_config_channel.json"

        if os.path.exists(dlpath + channel_config_path):
            incomplete_config = False
            incomplete_string = []
            # Load channel config
            channel_config = load_config(dlpath + channel_config_path)
            # Access settings
            if "c_max_resolution" in channel_config:
                if channel_config["c_max_resolution"] != "":
                    default_max_res = channel_config["c_max_resolution"]
            else:
                incomplete_config = True
                incomplete_string.append("c_max_resolution")

            if "c_ignore_min_duration" in channel_config:
                if channel_config["c_ignore_min_duration"] != "":
                    default_ignore_min_duration = channel_config["c_ignore_min_duration"]
            else:
                incomplete_config = True
                incomplete_string.append("c_ignore_min_duration")

            if "c_ignore_max_duration" in channel_config:
                if channel_config["c_ignore_max_duration"] != "":
                    default_ignore_max_duration = channel_config["c_ignore_max_duration"]
            else:
                incomplete_config = True
                incomplete_string.append("c_ignore_max_duration")

            if "c_only_restricted" in channel_config:
                if channel_config["c_only_restricted"] != "":
                    default_only_restricted = channel_config["c_only_restricted"]
            else:
                incomplete_config = True
                incomplete_string.append("c_only_restricted")

            if "c_skip_restricted" in channel_config:
                if channel_config["c_skip_restricted"] != "":
                    default_skip_restricted = channel_config["c_skip_restricted"]
            else:
                incomplete_config = True
                incomplete_string.append("c_skip_restricted")

            if "c_minimum_views" in channel_config:
                if channel_config["c_minimum_views"] != "":
                    default_minimum_views = channel_config["c_minimum_views"]
            else:
                incomplete_config = True
                incomplete_string.append("c_minimum_views")

            default_exclude_videos = channel_config["c_exclude_video_ids"]
            default_include_videos = channel_config["c_include_video_ids"]
            default_filter_words = channel_config["c_filter_words"]

            if incomplete_config:
                print(print_colored_text("\nFound ", BCOLORS.BLUE)
                      + print_colored_text("incomplete ", BCOLORS.ORANGE)
                      + print_colored_text("channel config file! --> Adding missing key(s) to file ", BCOLORS.BLUE)
                      + print_colored_text(str(incomplete_string) + "\n", BCOLORS.ORANGE))
                cc_check_and_update_channel_config(dlpath + channel_config_path, REQUIRED_CONFIG)
            else:
                print(print_colored_text("\nFound channel config file!\n", BCOLORS.BLUE))

        if video_id_from_single_video!="":
            default_include_videos = video_id_from_single_video

        limit_resolution_to = smart_input("Max. Resolution:  ", default_max_res)

        ignore_min_duration = smart_input("Ignore min_duration?  Y/n", default_ignore_min_duration)
        ignore_min_duration_bool = True
        if ignore_min_duration == "n":
            ignore_min_duration_bool = False
            print(print_colored_text("Ignoring Video(s) < " + str(min_duration) + " Minutes!", BCOLORS.RED))

        ignore_max_duration = smart_input("Ignore max_duration?  Y/n", default_ignore_max_duration)
        ignore_max_duration_bool = True
        if ignore_max_duration=="n":
            ignore_max_duration_bool = False
            print(print_colored_text("Ignoring Video(s) > " + str(max_duration) + " Minutes!", BCOLORS.RED))

        only_restricted_videos = smart_input("Only restricted video(s)?  Y/n", default_only_restricted)
        only_restricted_videos_bool = False
        if only_restricted_videos=="y":
            only_restricted_videos_bool = True
            print(print_colored_text("Downloading only restricted Video(s)!", BCOLORS.RED))

        skip_restricted_bool = False
        if not only_restricted_videos_bool:
            skip_restricted = smart_input("Skip restricted Video(s)?  Y/n ", default_skip_restricted)
            if skip_restricted == "y":
                skip_restricted_bool = True
                print(print_colored_text("Skipping restricted Video(s)!", BCOLORS.RED))

        min_video_views = int(smart_input("Minimum Views (0=disabled): ", default_minimum_views))
        if min_video_views > 0:
            min_video_views_bool = True
        else:
            min_video_views_bool = False

        exclude_video_ids = smart_input("\nExclude Video ID's (comma separated list): ", default_exclude_videos)
        exclude_list = []
        if exclude_video_ids!="":
            exclude_list = clean_youtube_urls(string_to_list(exclude_video_ids))

        include_video_ids = smart_input("Include Video ID's (comma separated list): ", default_include_videos)
        include_list = []
        if include_video_ids!="":
            include_list = clean_youtube_urls(string_to_list(include_video_ids))

        video_name_filter = str(smart_input("\nEnter filter word(s) (comma separated list): ", default_filter_words))
        video_name_filter_list = string_to_list(video_name_filter)

        count_total_videos = 0
        count_restricted_videos = 0
        count_ok_videos = 0
        count_this_run = 0
        count_skipped = 0

        video_watch_urls = []
        for url in c.video_urls:
            count_total_videos += 1
            if url.video_id not in exclude_list :
                if len(include_list)>0:
                    if url.video_id in include_list:
                        video_watch_urls.append(url.watch_url)
                else:
                    video_watch_urls.append(url.watch_url)

        print(f'\n\nTotal {count_total_videos} Video(s) by: \033[96m{c.channel_name}\033[0m\n')

        for url in video_watch_urls:
            only_video_id = pytubefix.extract.video_id(url)

            if not os.path.exists(dlpath):
                os.makedirs(dlpath)

            if find_file_by_string(dlpath, only_video_id, limit_resolution_to) != None:
                count_ok_videos += 1
                count_skipped += 1
                print(print_colored_text(f"\rSkipping {count_skipped} Videos", BCOLORS.MAGENTA), end="", flush=True)
            else:
                do_not_download = 0
                video = YouTube(youtube_base_url + only_video_id, on_progress_callback=on_progress)

                if video_name_filter=="" or any(word.lower() in video.title.lower() for word in video_name_filter_list):
                    if not ignore_min_duration_bool:
                        video_duration = int(video.length/60)
                        if video_duration < int(min_duration):
                            do_not_download = 1

                    if not ignore_max_duration_bool:
                        video_duration = int(video.length/60)
                        if video_duration > int(max_duration):
                            do_not_download = 1

                    if min_video_views > 0:
                        if video.views < min_video_views:
                            do_not_download = 1

                    if (video.age_restricted == False and
                            video.vid_info.get('playabilityStatus', {}).get('status') != 'UNPLAYABLE' and
                            do_not_download == 0 and not only_restricted_videos_bool):
                        print("\n")
                        count_ok_videos += 1
                        count_this_run += 1
                        count_skipped = 0
                        video_list.append(video.video_id)
                        download_video(video.video_id, count_ok_videos, len(video_watch_urls), video.views)
                    else:
                        if not skip_restricted_bool:
                            if (video.vid_info.get('playabilityStatus', {}).get('status') != 'UNPLAYABLE' and
                                    do_not_download == 0):
                                count_restricted_videos += 1
                                count_ok_videos += 1
                                count_this_run += 1
                                video_list_restricted.append(video.video_id)
                                download_video_restricted(video.video_id, count_ok_videos, len(video_watch_urls),
                                                        clean_string_regex(c.channel_name).rstrip(), video.views)

        if count_this_run == 0:
            print("\n\n" + print_colored_text("Nothing to do...\n\n", BCOLORS.GREEN))
        else:
            print(print_colored_text(f"\n\nDONE!\n", BCOLORS.GREEN))
            print(print_colored_text(f"Videos: {count_total_videos}, Selected Videos: {count_ok_videos}",
                                     BCOLORS.GREEN))
            print(print_colored_text(f"Downloaded in this session: {count_this_run}, (restricted: {len(video_list_restricted)} / ignored: {len(video_watch_urls)-count_ok_videos})",
                                     BCOLORS.GREEN))
            print(f"\n{get_free_space(dlpath)} free\n")

        continue_ytdl = smart_input("Continue?  Y/n ", "y")
        print("\n")
        if continue_ytdl=="y":
            continue
        else:
            break

    except Exception as e:
        delete_temp_files()
        print("An error occurred:", str(e))

        continue_ytdl = smart_input("There was an exception. Continue?  Y/n ", "y")
        print("\n")
        if continue_ytdl == "y":
            continue
        else:
            break

    except KeyboardInterrupt:
        delete_temp_files()
        print("\n\nGood Bye...\n")

        continue_ytdl = smart_input("There was an interrupt. Continue?  Y/n ", "y")
        print("\n")
        if continue_ytdl == "y":
            continue
        else:
            break
