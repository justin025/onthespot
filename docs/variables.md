# Variables Guide

This guide provides a detailed explanation of the variables available in **OnTheSpot** for customizing file names and organization of downloaded content.

---

## Universal Variables

These variables can be used across all file types to define naming and organizational conventions.

| **Variable**   | **Description**                                                                 |
| -------------- | ------------------------------------------------------------------------------- |
| `{service}`    | The name of the music service used to download the file (e.g., Spotify, Tidal). |
| `{service_id}` | The native ID of the track, album, or playlist on the selected music service.   |
| `{name}`       | The name of the track, album, or playlist.                                      |
| `{year}`       | The release year of the track, album, or playlist.                              |
| `{explicit}`   | Displays the explicit label if applicable (default: 🅴).                         |

---

## Audio-Specific Variables

These variables apply specifically to audio tracks and albums.

| **Variable**        | **Description**                                                 |
| ------------------- | --------------------------------------------------------------- |
| `{artist}`          | The name of the artist(s).                                      |
| `{album_artist}`    | The name of the album artist(s).                                |
| `{album_type}`      | The type of album (e.g., single, album, compilation).           |
| `{disc_number}`     | The disc number if the album has multiple discs.                |
| `{discccount}`      | The total number of discs in the album.                         |
| `{genre}`           | The genre of the track or album.                                |
| `{label}`           | The name of the record label.                                   |
| `{track_number}`    | The track number within the album.                              |
| `{trackcount}`      | The total number of tracks in the album.                        |
| `{isrc}`            | The International Standard Recording Code (ISRC) for the track. |
| `{playlist_name}`   | The name of the playlist (if part of a playlist).               |
| `{playlist_owner}`  | The owner or creator of the playlist.                           |
| `{playlist_number}` | The position of the track within the playlist.                  |

---

## Video-Specific Variables

These variables are applicable to videos, including movies and TV episodes.

| **Variable**       | **Description**                           |
| ------------------ | ----------------------------------------- |
| `{show_name}`      | The name of the show or series.           |
| `{season_number}`  | The season number of the show.            |
| `{episode_number}` | The episode number within the season.     |
| `{movie_title}`    | The title of the movie.                   |
| `{release_year}`   | The release year of the movie or episode. |

---

## Examples

| **Format**                                                     | **Result**                                         |
| -------------------------------------------------------------- | -------------------------------------------------- |
| `{artist} - {name}`                                            | `Artist Name - Song Title.mp3`                     |
| `{album_artist}/{album}/{track_number} - {name}`               | `Album Artist/Album Name/01 - Song Title.mp3`      |
| `{service}/{playlist_name}/{playlist_number} - {name}`         | `Spotify/Chill Playlist/01 - Relaxing Song.mp3`    |
| `{show_name}/Season {season_number}/{episode_number} - {name}` | `My Favorite Show/Season 2/03 - Episode Title.mp4` |

---

## Usage Tips

1. **Use Consistent Variables**: Ensure you use variables appropriate for the media type (e.g., audio or video).
2. **Check File Systems**: Avoid using variables that include characters not supported by your file system (e.g., `?`, `*`, `\`).
3. **Preview Formats**: Test your variable setup with a single download to ensure the format meets your expectations.

---

For more information, refer to the main configuration guide or reach out on the [community Discord](https://discord.gg/GCQwRBFPk9).

