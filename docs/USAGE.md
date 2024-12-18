# Usage Guide


## 1. Logging into your accounts
OnTheSpot supports various accounts and instructions for each are listed below, for further assistance please reach out for support on the community discord [here](https://discord.gg/GCQwRBFPk9).

- **Apple Music**: Enter the path to your Apple Music cookie in netscape format, the cookie can be deleted after the app has successfully logged in. To export your cookie you can use one of the following extensions, please note that I have not verified either of the extensions listed are secure, please use them at your own risk.
   - Firefox Extension: [Export Cookies](https://addons.mozilla.org/en-CA/firefox/addon/export-cookies-txt/)

   - Chrome Extension: [Get cookies.txt Clean](https://chromewebstore.google.com/detail/get-cookiestxt-clean/ahmnmhfbokciafffnknlekllgcnafnie)

- **Deezer**: Paste your ARL into the bar provided and click add account. To get your ARL log into the deezer website, open inspect element, navigate to application/storage, and open the deezer website's cookies. Your arl should be listed under one of the values provided.

- **Spotify**: Ensure that both OnTheSpot and the Spotify Desktop App are not restricted by a firewall or vpn so that they can communicate. Click add account and then head over to devices in the Spotify app. Under devices you should see 'OnTheSpot', select it. Once complete the app will prompt you to restart.

- **Tidal**: The app will provide you a link, open the link and login in your browser.


## 2. Searching and Downloading Music
The search bar is able to parse queries, urls, and text files.

If a query is provided, say 'Daft Punk' for instance, the app will provide results to the query seperated into categories: Tracks, Albums, Artists, Playlists, and depending on the music service Episodes, Podcasts, and Audiobooks.

If a url is provided the app will parse the url and immediately begin downloading.

If a file path is provided the app will parse each line in the file for urls beginning in either http:// or https:// and begin downloading the items listed.


## 4. Configuration

### General Configuration Options

   <details open>
   <summary><b>Open Configuration Table</b></summary>

| **Option** | **Description** |
| ------ | ------ |
| **Download Path** | Root folder where all downloaded media will be saved. |
| **Theme** | Choose the application theme (`light` or `dark`). |
| **Download Buttons** | Adds extra functionalities to the download queue. |
| **Show Thumbnails In Search/Downloads**| Display thumbnails on respective page. |
| **Thumbnail Size**|Change the size of thumbnail icons. |
| **Max Search Results** | Limits the number of search results displayed for each media type (e.g., songs, albums). |
| **Explicit Label** | Customize how explicit content is labeled in file names and the app (default: 🅴). |
| **Disable Bulk Download Notices** | Disables pop-up messages while downloading multiple songs or episodes. |
| **Mirror Spotify Playback** | Download currently playing song on the selected Spotify account |
| **Windows 10 Explorer Thumbnails** | Embed thumbnails in a format that respects Windows 10 explorer and media player, this is an older format of ID3 and not widely supported. |
| **Close To Tray** | Close application to tray on exit. |
| **Check for Updates** | Automatically check for application updates. |
| **File Bitrate** | Set the bitrate of a converted file, default value is 320k. This setting is not respected by lossless codecs, results may vary depending on your chosen filetype. |
| **File Hertz** | Set the hertz of a converted file, default value is 44100 |
| **Track/Episode Format** | Select the file format to output your downloaded tracks or podcasts (e.g. `mp3`, `m4a`, `flac`, `ogg`, `wav`). For a complete list of supported codecs please see the following [list](https://ffmpeg.org/ffmpeg-formats.html). |
| [**Track/Episode Path**](#trackplaylist-path-format) | Customize the file naming pattern for tracks, episodes, and playlists using variables like `{artist}`, `{album}`, etc. |
| **Use Custom Playlist Path** | Enable the use of a custom path format for playlists. |
| [**Playlist Path**](#trackplaylist-path-format) | Customize the file naming pattern for playlists using variables like `{artist}`, `{album}`, etc. |
| **Create M3U Files for Playlists** | If enabled create an M3U file for downloaded tracks in a playlist. |
| [**M3U Path**](#trackplaylist-path-format) | Customize the download path of created M3U files using variables like `{artist}`, `{album}`, etc. |
| [**EXTINF Seperator**](#trackplaylist-path-format) | M3U EXTINF metadata / list seperator. |
| [**EXTINF Path**](#trackplaylist-path-format) | Customize the M3U EXTINF label using variables like `{artist}`, `{album}`, etc. |
| **Save Album Cover** | Save album cover as an image with a default format of cover.png |
| **Album Cover Format** | The image format to save album covers in (default: png) |
| **Illegal Character Replacement** | Replace illegal characters in the filepath with the value specified (e.g., `/`, `\`, `<`, `>`, `*`, etc.). |
| **Download Lyrics\*** | Enable downloading of lyrics for each track/episode. *This feature may require a premium account.* |
| **Download Synced Lyrics Only\*** | Only download synced lyrics for tracks. *This feature may require a premium account.*|
| **Save LRC File\*** | Save lyrics in an `.lrc` file alongside the track. *This feature may require a premium account.*|
| **Rotate Active Account** | Automatically rotate between added accounts for downloading to minimize the chance of hitting rate limits. |
| **Raw Media Download** | Downloads an unmodified file from whatever service is selected. With this enabled file conversion and the embedding of any metadata is skipped. Lyrics and cover art will still be downloaded. |
| **Download Delay (s)** | The time,in seconds, to wait before initiating the next download. Helps prevent rate limits. |
| **Download Chunk Size (b)** | The chunk size, in bytes, in which to download files. |
| **Maximum Queue Workers** | Set the maximum number of queue workers. Setting a higher number will queue songs faster, only change this setting if you know what you're doing. Changes to this setting require you to restart the app take effect. |
| **Maximum Download Workers** | Set the maximum number of download workers. Only change this setting if you know what you're doing. Changes to this setting require you to restart the app to take effect. |
| **Translate File Path** | Translate file paths into the application language. |
| **Metadata Separator** | Set the separator for metadata fields with multiple values (default: `; `). |
| **Overwrite Existing Collection** | If a file already exists re-embed metadata in your selected format. |
| **Embed Metadata Tags** | Select which metadata tags to embed in downloaded files (e.g., `artist`, `album`, `year`, `lyrics`, etc.). |

   </details>


### Track/Episode/Playlist Path Format

- **Customize File Names**
  - Define how downloaded tracks are named using variables enclosed in `{}`.

- **Available Variables**

   <details open>
   <summary><b>Open Variables Table</b></summary>

   | **Variable**      | **Description**                                     |
   | ----------------- | --------------------------------------------------- |
   | `{service}`       | The music service used to download your file        |
   | `{artist}`        | Name of the artist(s).                              |
   | `{album_artist}`  | Name of the album artist(s).                        |
   | `{album_type}`    | Name of the artist type (single, album, etc).       |
   | `{name}`          | Name of the track.                                  |
   | `{year}`          | Release year of the track.                          |
   | `{track_number}`  | Track number on the album.                          |
   | `{trackcount}`    | Total number of tracks in the album                 |
   | `{disc_number}`   | Disc number (if applicable).                        |
   | `{discccount}`    | Total number of discs in the album (if applicable). |
   | `{genre}`         | Genre of the song.                                  |
   | `{label}`         | Name of the record label.                           |
   | `{explicit}`      | Displays 'Explicit Label' if the song is marked explicit (default: 🅴). |
   | `{playlist_name}` | Name of the playlist (if part of a playlist).       |
   | `{playlist_owner}`| Name of the playlist owner (if part of a playlist). |
   | `{playlist_number}`| Item number in a playlist (if part of a playlist). |
   </details>

> [!TIP]
> **Example:**
> Setting the format to `{artist} - {name}.mp3` will result in files named like `Artist Name - Song Title.mp3`.


## 6. Saving Your Configuration

- **Apply Changes**
  - After adjusting any settings, click the 'Save Settings' button to apply your changes. Some configuration changes may require restarting the app to take effect.
