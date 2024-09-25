<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../../Assets/01_Logo/LOGO-HERE">
  <source media="(prefers-color-scheme: light)" srcset="../../Assets/01_Logo/LOGO-HERE">
  <img src="../../Assets/01_Logo/LOGO-HERE" alt="Logo of OnTheSpot" width="200">
</picture>

<br>

# Basic Usage

- [Basic Usage](#basic-usage)
  - [1. Getting Started](#1-getting-started)
  - [2. Searching and Downloading Music](#2-searching-and-downloading-music)
    - [Search by Query](#search-by-query)
    - [Download by URL](#download-by-url)
  - [3. Monitoring Download Status](#3-monitoring-download-status)
  - [4. Configuration](#4-configuration)
    - [General Configuration Options](#general-configuration-options)
  - [5. Advanced Configuration](#5-advanced-configuration)
    - [Track Naming Format](#track-naming-format)
    - [Album Directory Naming](#album-directory-naming)
    - [Additional Advanced Options](#additional-advanced-options)
  - [6. Saving Your Configuration](#6-saving-your-configuration)

<br>

## 1. Getting Started

> [!WARNING]
> When launching the application for the first time, you will receive a warning that no Spotify accounts are added.

1. **Dismiss the Warning**
   - Click the close button on the warning dialog.

2. **Add Your Spotify Account(s)**
   - Navigate to the **Configuration** tab.
   - Scroll to the bottom and add your Spotify account(s).

> [!TIP]
> Adding multiple accounts allows you to download multiple songs simultaneously, speeding up the download process.

[Youtube Video Explaining the Usage]

## 2. Searching and Downloading Music

### Search by Query

1. **Navigate to the Search Tab**
   - Click on the **Search** tab within the application.

2. **Enter Your Search Terms**
   - Type the name of a song, artist, album, or playlist into the search bar.

3. **Execute the Search**
   - Click the **Search** button to retrieve results.

4. **Download Music**
   - **Single Download**: Click the **Download** button next to the desired item.
   - **Bulk Download**: Use the buttons below the results table to download multiple items at once.

> [!NOTE]
> Downloading large media types like albums or playlists may take longer. The application might appear unresponsive during this process—please be patient.

### Download by URL

1. **Enter the URL**
   - Paste the Spotify URL of a song, album, artist, or playlist into the search field.

2. **Start the Download**
   - Click the **Download** button to begin downloading.

3. **Bulk URL Downloads**
   - You can also provide a path to a text file containing multiple URLs. OnTheSpot will queue all listed URLs for downloading.

> [!IMPORTANT]
> Ensure each URL in the text file is on a separate line to avoid errors during the download process.

> [!NOTE]
> Similar to bulk downloads via query, downloading media types other than 'Tracks' may take longer and cause the app to appear frozen temporarily.

## 3. Monitoring Download Status

- **Progress Tab**
  - Click on the **Progress** tab to monitor your downloads.
  
  | **Status Indicator** | **Description**                                |
  | -------------------- | ---------------------------------------------- |
  | Downloading          | The song is currently being downloaded.        |
  | Completed            | The song has been successfully downloaded.     |
  | Error                | An issue occurred during the download process. |

> [!TIP]
> From the **Progress** tab, you can pause, resume, or cancel ongoing downloads as needed.

[GIF Image how to Monitor]

## 4. Configuration

Customize **OnTheSpot** to fit your preferences by adjusting the settings in the Configuration tab.

### General Configuration Options

| **Option**                           | **Description**                                                                                                                                                                                |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Max Download Workers**             | Number of simultaneous download threads. Set this to match the number of Spotify accounts you've added. *Requires application restart to take effect.*                                         |
| **Active Account Number**            | Select which Spotify account to use for searches and downloads. Accounts are numbered in the accounts list.                                                                                    |
| **Download Location**                | Choose the root folder where all downloaded media will be saved.                                                                                                                               |
| **Download Delay**                   | Time (in seconds) to wait before initiating the next download after a successful one. Helps prevent hitting Spotify's rate limits.                                                             |
| **Max Retries**                      | Number of retry attempts for a failed download before skipping to the next item.                                                                                                               |
| **Max Search Results**               | Limits the number of search results displayed for each media type (e.g., songs, albums). For example, setting this to '1' shows one result for each type, resulting in 4 total search results. |
| **Raw Media Download**               | Downloads original audio files in `.ogg` format without converting or adding metadata. *Disables metadata writing and thumbnail embedding.*                                                    |
| **Force Premium**                    | Use this option if your premium account is mistakenly recognized as free. **Caution:** Only enable if you are certain your account is premium.                                                 |
| **Mirror Playback**                  | Automatically downloads songs you play in the Spotify app, building a library of frequently listened tracks.                                                                                   |
| **Show/Hide Advanced Configuration** | Toggle to display or hide the Advanced Configuration settings.                                                                                                                                 |
| **Save Settings**                    | Click to apply and save any changes made to the configuration options.                                                                                                                         |

> [!IMPORTANT]
> After making changes to the configuration, always click the **Save Settings** button to ensure your preferences are applied.

## 5. Advanced Configuration

For users who want more control over how their music is organized and downloaded.

### Track Naming Format

- **Customize File Names**
  - Define how downloaded tracks are named using variables enclosed in `{}`.

- **Available Variables**

  | **Variable**      | **Description**                                     |
  | ----------------- | --------------------------------------------------- |
  | `{artist}`        | Name of the artist.                                 |
  | `{album}`         | Name of the album.                                  |
  | `{name}`          | Name of the track.                                  |
  | `{rel_year}`      | Release year of the track.                          |
  | `{track_number}`  | Track number on the album.                          |
  | `{disc_number}`   | Disc number (if applicable).                        |
  | `{playlist_name}` | Name of the playlist (if part of a playlist).       |
  | `{genre}`         | Genre of the song.                                  |
  | `{label}`         | Name of the record label.                           |
  | `{explicit}`      | Displays 'Explicit' if the song is marked explicit. |
  | `{spotid}`        | Spotify ID of the track.                            |

> [!TIP]
> **Example:**  
> Setting the format to `{artist} - {name}.mp3` will result in files named like `Artist Name - Song Title.mp3`.

### Album Directory Naming

- **Organize by Folders**
  - Define how albums are organized into directories using variables.

- **Available Variables**

  | **Variable**      | **Description**                               |
  | ----------------- | --------------------------------------------- |
  | `{artist}`        | Name of the main artist of the album.         |
  | `{album}`         | Name of the album.                            |
  | `{rel_year}`      | Release year of the album.                    |
  | `{playlist_name}` | Name of the playlist (if part of a playlist). |
  | `{genre}`         | Genre of the album.                           |

> [!TIP]
> **Example:**  
> Setting the directory format to `{artist}/{album} ({rel_year})` will create folders like `Artist Name/Album Title (2021)/`.

### Additional Advanced Options

| **Option**                            | **Description**                                                                                                                                                                                                      |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Download Buttons**                  | Adds extra functionalities like copying song links, liking songs on Spotify, playing tracks, and locating local files.                                                                                               |
| **Rotate Active Account Number**      | Automatically switches between added accounts for downloading to minimize the chance of hitting rate limits.                                                                                                         |
| **Disable Bulk Download Notices**     | Turns off pop-up messages that appear during bulk downloads, providing a cleaner user experience.                                                                                                                    |
| **Recoverable Downloads Retry Delay** | Sets the wait time before retrying a failed download attempt.                                                                                                                                                        |
| **Skip Bytes at End**                 | Adjusts the number of bytes to skip when encountering download errors at the end of tracks. *Default is 167 bytes.* Set to `0` if you experience 'decode errors' or incomplete downloads.                            |
| **Force Artist/Album Directories**    | - **Enable:** Organizes all downloads into artist and album folders, even for single tracks or playlists.                                                                                                            |
|                                       | - **Disable:** Saves downloads directly into the main download folder without additional subfolders.                                                                                                                 |
| **Media Format**                      | Select the audio format for your downloaded music (e.g., `mp3`, `flac`). **Note:** Do not include a dot before the format (use `mp3`, not `.mp3`). This setting is ignored when using the Raw Media Download option. |

> [!CAUTION]
> Changing some advanced settings may affect the organization and quality of your downloaded music. Proceed with adjustments only if you are familiar with the options.

---

## 6. Saving Your Configuration

- **Apply Changes**
  - After adjusting any settings, click the **Save Settings** button to apply your changes.

> [!IMPORTANT]
> Some configuration changes may require restarting **OnTheSpot** to take effect. Make sure to restart the application if prompted.

[GIF Image how to Save]

<br>

---

> [⮝ **Go to the Installation** ⮝](Basic-Usage.md)

---

> [⮝ **Go back to the ReadMe** ⮝](../)

---
