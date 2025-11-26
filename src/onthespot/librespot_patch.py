"""OnTheSpot librespot metadata patch."""

import logging
from typing import Type

try:
    from librespot.core import ApiClient
    from librespot.mercury import RawMercuryRequest
    from librespot.proto import Metadata_pb2 as MetadataProto
except Exception as exc:
    logging.getLogger("onthespot.librespot_patch").warning(
        "librespot is unavailable; Spotify downloads may remain broken: %s",
        exc,
    )
else:
    _LOGGER = logging.getLogger("onthespot.librespot_patch")

    _ORIGINAL_TRACK = ApiClient.get_metadata_4_track
    _ORIGINAL_EPISODE = ApiClient.get_metadata_4_episode
    _ORIGINAL_ALBUM = ApiClient.get_metadata_4_album
    _ORIGINAL_ARTIST = ApiClient.get_metadata_4_artist
    _ORIGINAL_SHOW = ApiClient.get_metadata_4_show

    def _fetch_via_mercury(self: ApiClient, uri: str, proto_cls: Type) -> object:
        """Return the requested metadata via Mercury; fallback to HTTP."""
        session = getattr(self, "_ApiClient__session", None)
        if session is None:
            raise RuntimeError("librespot ApiClient is not authenticated yet")

        try:
            response = session.mercury().send_sync(RawMercuryRequest.get(uri))
            if response.status_code != 200 or not response.payload:
                raise RuntimeError(f"Mercury metadata request failed ({response.status_code})")

            proto = proto_cls()
            proto.ParseFromString(response.payload)
            return proto
        except Exception as error:
            _LOGGER.warning(
                "Mercury metadata request for %s failed (%s); falling back to HTTP",
                uri,
                error,
            )
            raise

    def _ensure_hex_id(identifier, kind: str) -> str:
        if hasattr(identifier, "hex_id"):
            return identifier.hex_id()
        raise TypeError(f"Expected object with hex_id() for {kind} metadata lookups")

    def _patched_get_metadata_4_track(self: ApiClient, track_id):
        uri = f"hm://metadata/4/track/{_ensure_hex_id(track_id, 'track')}"
        try:
            return _fetch_via_mercury(self, uri, MetadataProto.Track)
        except Exception:
            return _ORIGINAL_TRACK(self, track_id)

    def _patched_get_metadata_4_episode(self: ApiClient, episode_id):
        uri = f"hm://metadata/4/episode/{_ensure_hex_id(episode_id, 'episode')}"
        try:
            return _fetch_via_mercury(self, uri, MetadataProto.Episode)
        except Exception:
            return _ORIGINAL_EPISODE(self, episode_id)

    def _patched_get_metadata_4_album(self: ApiClient, album_id):
        uri = f"hm://metadata/4/album/{_ensure_hex_id(album_id, 'album')}"
        try:
            return _fetch_via_mercury(self, uri, MetadataProto.Album)
        except Exception:
            return _ORIGINAL_ALBUM(self, album_id)

    def _patched_get_metadata_4_artist(self: ApiClient, artist_id):
        uri = f"hm://metadata/4/artist/{_ensure_hex_id(artist_id, 'artist')}"
        try:
            return _fetch_via_mercury(self, uri, MetadataProto.Artist)
        except Exception:
            return _ORIGINAL_ARTIST(self, artist_id)

    def _patched_get_metadata_4_show(self: ApiClient, show_id):
        uri = f"hm://metadata/4/show/{_ensure_hex_id(show_id, 'show')}"
        try:
            return _fetch_via_mercury(self, uri, MetadataProto.Show)
        except Exception:
            return _ORIGINAL_SHOW(self, show_id)

    ApiClient.get_metadata_4_track = _patched_get_metadata_4_track  # type: ignore[assignment]
    ApiClient.get_metadata_4_episode = _patched_get_metadata_4_episode  # type: ignore[assignment]
    ApiClient.get_metadata_4_album = _patched_get_metadata_4_album  # type: ignore[assignment]
    ApiClient.get_metadata_4_artist = _patched_get_metadata_4_artist  # type: ignore[assignment]
    ApiClient.get_metadata_4_show = _patched_get_metadata_4_show  # type: ignore[assignment]
