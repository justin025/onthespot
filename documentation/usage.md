<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/01_Logo/Cover_White.png">
  <source media="(prefers-color-scheme: light)" srcset="../assets/01_Logo/Cover_Black.png">
  <img src="../assets/01_Logo/Cover_White.png" alt="Logo of OnTheSpot" width="350">
</picture>

<br>

# Getting Started

When launching the application for the first time, you will receive a warning that no Spotify accounts are added.

1. **Dismiss the Warning**
   - Click the close button on the warning dialog.

2. **Add Your Spotify Account(s)**
   - Navigate to the **Configuration** tab.
   - Scroll to the bottom and add your Spotify account(s).

> [!TIP]
> Adding multiple accounts allows you to download multiple songs simultaneously, speeding up the download process.

[WIP: Youtube Video Explaining the Usage]

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
> Downloading large media types like albums or playlists may take longer. The application might appear unresponsive during this process. Please be patient.

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

## 4. Configuration

Customize **OnTheSpot** to fit your preferences by adjusting the settings in the Configuration tab.

### General Configuration Options

<details>
  <summary  style="color: red"><b>Open Options Table</b></summary>

  | **Option** | **Description** |
  | ------ | ------ |
  | **Version** | Version of the application. |
  | **Check for Updates** | Automatically check for application updates. |
  | **Max Download Workers** | Number of simultaneous download threads. Set this to match the number of Spotify accounts you've added. Requires application restart to take effect. |
  | **Rotate Active Account** | Automatically switch between added accounts for downloading to minimize the chance of hitting rate limits. |
  | **Download Location** | Root folder where all downloaded media will be saved. |
  | **Download Delay** | Time (in seconds) to wait before initiating the next download. Helps prevent Spotify's rate limits. |
  | **Max Retries** | Number of retry attempts for a failed download before skipping to the next item. |
  | **Max Search Results** | Limits the number of search results displayed for each media type (e.g., songs, albums). |
  | **Media Format** | Select the audio format for your downloaded music or podcasts (e.g., `mp3`, `flac`). |
  | [**Track/Episode Path Format**](#trackplaylist-path-format) | Customize the file naming pattern for tracks, episodes, and playlists using variables like `{artist}`, `{album}`, etc. |
  | **Download Lyrics** | Enable downloading of lyrics for each track. |
  | **Save LRC File** | Save lyrics in an `.lrc` file alongside the track. |
  | **Force Premium** | Enforce high-quality downloads (requires a premium account). |
  | **Show Search Thumbnails**| Display thumbnails next to search results. |
  | **Metadata Separator** | Set the separator for metadata fields with multiple values (default: `;`). |
  | **Embed Metadata Tags** | Select which metadata tags to embed in downloaded files (e.g., `artist`, `album`, `year`, `lyrics`, etc.). |
  | **Explicit Label** | Customize how explicit content is labeled in file names and the app (default: 🅴). |
  | **Theme** | Choose the application theme (`light` or `dark`). |

</details>

> [!IMPORTANT]
> After making changes to the configuration, always click the **Save Settings** button to ensure your preferences are applied.

## 5. Advanced Configuration

For users who want more control over how their music is organized and downloaded.

### Track/Playlist Path Format

- **Customize File Names**
  - Define how downloaded tracks are named using variables enclosed in `{}`.

- **Available Variables**

   <details>
   <summary style="color: red"><b>Open Variables Table</b></summary>

   | **Variable**      | **Description**                                     |
   | ----------------- | --------------------------------------------------- |
   | `{artist}`        | Name of the artist(s).                              |
   | `{album}`         | Name of the album.                                  |
   | `{name}`          | Name of the track.                                  |
   | `{rel_year}`      | Release year of the track.                          |
   | `{track_number}`  | Track number on the album.                          |
   | `{disc_number}`   | Disc number (if applicable).                        |
   | `{playlist_name}` | Name of the playlist (if part of a playlist).       |
   | `{genre}`         | Genre of the song.                                  |
   | `{label}`         | Name of the record label.                           |
   | `{explicit}`      | Displays 'Explicit Label' if the song is marked explicit (default: 🅴). |
   | `{spotid}`        | Spotify ID of the track.                            |

   </details>

> [!TIP]
> **Example:**  
> Setting the format to `{artist} - {name}.mp3` will result in files named like `Artist Name - Song Title.mp3`.

### Podcast Path Format

- **Organize by Folders**
  - Define how podcasts are organized into directories using variables.

- **Available Variables**

   <details>
   <summary style="color: red"><b>Open Variables Table</b></summary>

  | **Variable**      | **Description**                               |
  | ----------------- | --------------------------------------------- |
  | `{artist}`        | Name of the artist(s).                        |
  | `{podcast_name}`  | Name of the Podcast.                          |
  | `{episode_name}`  | Episode name.                                 |
  | `{release_date}`  | Episode release date.                         |
  | `{total_episodes}`| Total number of episodes in podcast.          |
  | `{language}`      | Podcast language.                             |

   </details>

> [!TIP]
> **Example:**  
> Setting the directory format to `{artist}/{podcast_name}/{episode})` will create folders like `Artist Name/Podcast Name/Episode Name.mp3`.

### Additional Advanced Options

   <details>
   <summary style="color: red"><b>Open Advanced Options</b></summary>

| **Option**                          | **Description**                                                                                                                                                                               |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Use Custom Playlist Path**         | Enable the use of a custom path format for playlists.                                                                                                                                          |
| **Download Buttons**                 | Adds extra functionalities like copying song links, opening tracks in your local music player, and locating the download directory.                                                             |
| **Recoverable Downloads Retry Delay**| Sets the wait time before retrying a failed download attempt (default: `10 seconds`).                                                                                                          |
| **Skip Bytes at End**                | Sets the number of bytes to skip at the end of a download when encountering 'PD Errors' to avoid incomplete tracks.                                                                             |
| **Disable Bulk Download Notices**    | Disables pop-up messages during bulk downloads for a cleaner user experience.                                                                                                                  |
| **Translate File Path**              | Translate file paths into the application language.                                                                                                                                           |

   </details>

> [!CAUTION]
> Changing some advanced settings may affect the organization and quality of your downloaded music. Proceed with adjustments only if you are familiar with the options.

## 6. Saving Your Configuration

- **Apply Changes**
  - After adjusting any settings, click the **Save Settings** button on the right to apply your changes.

> [!IMPORTANT]
> Some configuration changes may require restarting **OnTheSpot** to take effect. Make sure to restart the application if prompted.
