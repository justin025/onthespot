# Integration Guide

This guide explains how to integrate **OnTheSpot** with various platforms, services, and tools.

---

## Supported Integrations

### Music Streaming Services

| **Service**            | **Integration Steps**                                                                                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Apple Music**        | Obtain `media-user-token` by logging into [Apple Music](https://music.apple.com) via Chrome, opening Developer Tools (Ctrl + Shift + I), and copying the `media-user-token` cookie. |
| **Bandcamp**           | Simply click 'Add Bandcamp Account' in OnTheSpot and restart the app. No account is required.                                                                                       |
| **Deezer**             | Paste the `arl` value obtained from cookies (via Developer Tools on the Deezer website) into OnTheSpot.                                                                             |
| **Qobuz**              | Enter email and password, or use `user_auth_token` in the config file. Restart the app after updating credentials.                                                                  |
| **SoundCloud**         | Add the account in OnTheSpot and restart. No login is required for public downloads.                                                                                                |
| **Spotify**            | Add the account, then select "OnTheSpot" under "Devices" in the Spotify Desktop App to sync.                                                                                        |
| **Tidal**              | Follow the login link provided by OnTheSpot and authenticate in your browser.                                                                                                       |
| **YouTube Music**      | Simply click 'Add YouTube Music Account' in OnTheSpot and restart the app.                                                                                                          |
| **Generic Downloader** | Activate the "Generic Downloader" in OnTheSpot. Paste supported URLs (see [yt-dlp extractors](https://github.com/yt-dlp/yt-dlp/tree/master/yt_dlp/extractor)) to download media.    |

---

### Searching and Downloading Music

| **Action**          | **Steps**                                                                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Search by Query** | Enter a query (e.g., "Daft Punk") in the search bar. Results will be categorized into Tracks, Albums, Artists, Playlists, Episodes, Podcasts, and Audiobooks (where supported). |
| **Search by URL**   | Paste a URL into the search bar. OnTheSpot will parse and download the linked content automatically.                                                                            |
| **Search by File**  | Provide a file path containing URLs (one per line). OnTheSpot will parse and download all listed media.                                                                         |

---

### Metadata and Download Settings

| **Setting**                | **Description**                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Metadata Tags**          | Choose which tags (e.g., artist, album, year) are embedded in downloaded files.                        |
| **File Format**            | Specify output formats for tracks, episodes, playlists, or videos (e.g., MP3, FLAC, MP4).              |
| **Custom Paths**           | Use variables (e.g., `{artist}`, `{album}`, `{name}`) to define how files and playlists are organized. |
| **Max Search Results**     | Limit the number of results displayed per category during searches.                                    |
| **Download Workers**       | Set the maximum number of simultaneous downloads.                                                      |
| **Retry Worker and Delay** | Automatically retry failed downloads after a specified delay.                                          |
| **Download Delay**         | Add a delay (in seconds) between downloads to avoid hitting service rate limits.                       |
| **Save Album Covers**      | Save album covers as standalone image files (default: `cover.png`).                                    |
| **Download Lyrics**        | Enable lyrics download for tracks. Requires a premium account on some services.                        |

---

### Tips for Optimizing Integrations

| **Tip**                  | **Description**                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| **Rotate Accounts**      | Enable "Rotate Active Account" to distribute downloads across multiple accounts and avoid rate limits. |
| **Embed Thumbnails**     | Activate "Windows Explorer Thumbnails" for better media browsing on Windows.                           |
| **Backup Configuration** | Regularly back up your `config.json` file to avoid losing your integration and setup details.          |
| **Use Web UI**           | Enable WebUI for remote access to OnTheSpot functionalities.                                           |

---

For further assistance, refer to the community Discord [here](https://discord.gg/GCQwRBFPk9).

