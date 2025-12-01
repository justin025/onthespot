import os
# Required for librespot-python
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import traceback
from flask import Flask, jsonify, render_template, redirect, request, send_file, url_for, flash, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from .accounts import FillAccountPool, get_account_token
from .api.apple_music import apple_music_get_track_metadata, apple_music_add_account
from .api.bandcamp import bandcamp_get_track_metadata
from .api.deezer import deezer_get_track_metadata, deezer_add_account
from .api.qobuz import qobuz_get_track_metadata, qobuz_add_account
from .api.soundcloud import soundcloud_get_track_metadata, soundcloud_add_account
from .api.spotify import MirrorSpotifyPlayback, spotify_new_session, spotify_get_track_metadata, spotify_get_podcast_episode_metadata
from .api.tidal import tidal_get_track_metadata
from .api.youtube_music import youtube_music_get_track_metadata, youtube_music_add_account
from .api.crunchyroll import crunchyroll_get_episode_metadata, crunchyroll_add_account
from .api.generic import generic_add_account
try:
    from .api.plex import plex_api
    PLEX_AVAILABLE = True
except Exception as e:
    print(f"WARNING: Failed to import Plex API: {e}")
    PLEX_AVAILABLE = False
    plex_api = None
from .downloader import DownloadWorker, RetryWorker
from .otsconfig import cache_dir, config_dir, config
from .parse_item import parsingworker, parse_url
from .runtimedata import get_logger, account_pool, pending, download_queue, download_queue_lock, pending_lock, parsing, parsing_lock, register_worker, kill_all_workers, set_worker_restart_callback
from .search import get_search_results
from .utils import format_bytes

logger = get_logger("web")
os.environ['FLASK_ENV'] = 'production'
web_resources = os.path.join(config.app_root, 'resources', 'web')
app = Flask('OnTheSpot', template_folder=web_resources, static_folder=web_resources)
app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)


class QueueWorker(threading.Thread):
    def __init__(self):
        super().__init__()
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                if pending:
                    local_id = next(iter(pending))
                    with pending_lock:
                        item = pending.pop(local_id)
                    token = get_account_token(item['item_service'])
                    item_metadata = globals()[f"{item['item_service']}_get_{item['item_type']}_metadata"](token, item['item_id'])
                    if item_metadata:
                        with download_queue_lock:
                            download_queue[local_id] = {
                                'local_id': local_id,
                                'available': True,
                                "item_service": item["item_service"],
                                "item_type": item["item_type"],
                                'item_id': item['item_id'],
                                'item_status': 'Waiting',
                                "file_path": None,
                                "item_name": item_metadata["title"],
                                "item_by": item_metadata["artists"],
                                'parent_category': item['parent_category'],
                                'playlist_name': item.get('playlist_name'),
                                'playlist_by': item.get('playlist_by'),
                                'playlist_number': item.get('playlist_number'),
                                'track_number': item_metadata.get('track_number'),
                                'album_name': item_metadata.get('album_name'),
                                'item_album_name': item_metadata.get('album_name'),
                                'item_thumbnail': item_metadata["image_url"],
                                'item_url': item_metadata["item_url"],
                                'progress': 0
                            }
                else:
                    time.sleep(0.2)
            except Exception as e:
                logger.error(f"Unknown Exception for {item}: {str(e)}\nTraceback: {traceback.format_exc()}")
                with pending_lock:
                    pending[local_id] = item

    def stop(self):
        logger.info('Stopping Queue Worker')
        self.is_running = False
        self.join(timeout=5)


class AutoClearWorker(threading.Thread):
    """
    Worker that automatically clears completed downloads after all items are done.
    Waits 60 seconds after the queue is fully complete before clearing.
    """
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.last_all_done_time = None
        self.CLEAR_DELAY_SECONDS = 60

    def run(self):
        logger.info('AutoClearWorker started')
        while self.is_running:
            try:
                time.sleep(5)  # Check every 5 seconds

                with download_queue_lock:
                    if not download_queue:
                        # Queue is empty, reset timer
                        self.last_all_done_time = None
                        continue

                    # Check if all items are in a "done" state
                    all_done = True
                    for local_id, item in download_queue.items():
                        status = item.get("item_status", "")
                        if status not in ("Downloaded", "Already Exists", "Cancelled", "Unavailable", "Deleted", "Failed"):
                            # Found an item that's still in progress
                            all_done = False
                            break

                    if all_done:
                        # All items are done
                        if self.last_all_done_time is None:
                            # First time we've noticed everything is done
                            self.last_all_done_time = time.time()
                            logger.info(f"All downloads complete. Will auto-clear in {self.CLEAR_DELAY_SECONDS} seconds...")
                        else:
                            # Check if enough time has passed
                            elapsed = time.time() - self.last_all_done_time
                            if elapsed >= self.CLEAR_DELAY_SECONDS:
                                # Time to clear!
                                logger.info("Auto-clearing completed downloads...")
                                keys_to_delete = []
                                for local_id, item in download_queue.items():
                                    if item["item_status"] in ("Downloaded", "Already Exists", "Cancelled", "Unavailable", "Deleted"):
                                        keys_to_delete.append(local_id)

                                for key in keys_to_delete:
                                    del download_queue[key]

                                logger.info(f"Auto-cleared {len(keys_to_delete)} items from download queue")
                                self.last_all_done_time = None
                    else:
                        # Not all items are done, reset timer
                        if self.last_all_done_time is not None:
                            logger.debug("New downloads detected, resetting auto-clear timer")
                        self.last_all_done_time = None

            except Exception as e:
                logger.error(f"Error in AutoClearWorker: {str(e)}\nTraceback: {traceback.format_exc()}")
                time.sleep(5)

    def stop(self):
        logger.info('Stopping AutoClear Worker')
        self.is_running = False
        self.join(timeout=5)


class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


login_manager.login_view = "/login"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not config.get('use_webui_login') or not config.get('webui_username'):
        user = User('guest')
        login_user(user)
        return redirect(url_for('search'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == config.get('webui_username') and password == config.get('webui_password'):
            user = User(username)
            login_user(user)
            return redirect(url_for('search'))
        flash('Invalid credentials, please try again.')
    return render_template('login.html')


@app.route('/api/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/icons/<path:filename>')
def serve_icons(filename):
    icon_path = os.path.join(config.app_root, 'resources', 'icons', filename)
    return send_file(icon_path)


@app.route('/')
@login_required
def index():
    return redirect(url_for('search'))


@app.route('/search')
@login_required
def search():
    config_path = os.path.join(config_dir(), 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('search.html', config=config_data)


@app.route('/download_queue')
@login_required
def download_queue_page():
    config_path = os.path.join(config_dir(), 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('download_queue.html', config=config_data)


@app.route('/settings')
@login_required
def settings():
    config_path = os.path.join(config_dir(), 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('settings.html', config=config_data, account_pool=account_pool)


@app.route('/about')
@login_required
def about():
    return render_template('about.html', version=config.get("version"), statistics=f"{config.get('total_downloaded_items')} / {format_bytes(config.get('total_downloaded_data'))}")


@app.route('/api/search_results')
@login_required
def search_results():
    query = request.args.get('q')

    # Read filter states from URL parameters, default to only albums
    content_types = []
    if request.args.get('tracks') == 'true':
        content_types.append('track')
    if request.args.get('playlists') == 'true':
        content_types.append('playlist')
    if request.args.get('albums') == 'true':
        content_types.append('album')
    if request.args.get('artists') == 'true':
        content_types.append('artist')
    if request.args.get('podcasts') == 'true':
        content_types.append('show')
    if request.args.get('episodes') == 'true':
        content_types.append('episode')
    if request.args.get('audiobooks') == 'true':
        content_types.append('audiobook')

    # If no filters specified, default to albums only
    if not content_types:
        content_types = ['album']

    results = get_search_results(query, content_types=content_types)

    # Handle special return values
    if results is True:
        # URL was parsed and added to queue
        return jsonify({
            'success': True,
            'message': 'Item is being parsed and will be added to the download queue shortly.',
            'results': []
        })
    elif results is False:
        return jsonify({
            'success': False,
            'message': 'Invalid item, please check your query or account settings.',
            'results': []
        })
    elif results is None:
        return jsonify({
            'success': False,
            'message': 'You need to login to at least one account to use this feature.',
            'results': []
        })
    elif isinstance(results, list):
        # Return search results array (including Spotify ID lookups)
        return jsonify({
            'success': True,
            'results': results
        })
    else:
        # Unexpected return type
        return jsonify({
            'success': False,
            'message': 'Unexpected error occurred.',
            'results': []
        })


@app.route('/api/clear_items', methods=['POST'])
@login_required
def clear_items():
    keys_to_delete = []
    for local_id, item in download_queue.items():
        if item["item_status"] in ("Downloaded", "Already Exists", "Cancelled", "Unavailable", "Deleted"):
            keys_to_delete.append(local_id)
    for key in keys_to_delete:
        del download_queue[key]
    return jsonify(success=True)


@app.route('/api/cancel_items', methods=['POST'])
@login_required
def cancel_items():
    """Cancel all pending and waiting items, and mark downloading items for cancellation."""
    # Clear parsing queue
    with parsing_lock:
        parsing.clear()
    
    # Clear pending queue
    with pending_lock:
        pending.clear()
    
    # Cancel all items in download queue that are waiting or downloading
    with download_queue_lock:
        for local_id, item in download_queue.items():
            if item["item_status"] in ("Waiting", "Downloading"):
                download_queue[local_id]['item_status'] = 'Cancelled'
    
    return jsonify(success=True)


@app.route('/api/retry_items', methods=['POST'])
@login_required
def retry_items():
    # First, check if there are any failed downloads
    has_failed_downloads = False
    with download_queue_lock:
        for local_id, item in download_queue.items():
            if item["item_status"] in ("Failed", "Cancelled"):
                has_failed_downloads = True
                break

    # If there are failed downloads, force reconnect all Spotify accounts
    if has_failed_downloads:
        logger.info("Found failed downloads - forcing Spotify account reconnection before retry")
        from .api.spotify import spotify_re_init_session

        reconnected_count = 0
        for account_idx, account in enumerate(account_pool):
            if account.get('service') == 'spotify' and account.get('login', {}).get('session'):
                try:
                    logger.info(f"Reconnecting Spotify account {account_idx}: {account.get('username', 'unknown')}")
                    spotify_re_init_session(account)
                    account['last_session_time'] = time.time()
                    reconnected_count += 1
                except Exception as e:
                    logger.error(f"Failed to reconnect Spotify account {account_idx}: {e}")

        if reconnected_count > 0:
            logger.info(f"Successfully reconnected {reconnected_count} Spotify account(s) - now retrying failed downloads")

    # Now retry the failed/cancelled downloads
    with download_queue_lock:
        for local_id, item in download_queue.items():
            if item["item_status"] in ("Failed", "Cancelled"):
                download_queue[local_id]['item_status'] = 'Waiting'
                download_queue[local_id]['available'] = True
    return jsonify(success=True)


@app.route('/api/restart', methods=['POST'])
@login_required
def restart():
    logger.info("Caching Download Queue...")
    with open(os.path.join(cache_dir(), 'cached_download_queue.txt'), 'w') as file:
        for local_id, item in download_queue.items():
            file.write(item['item_url'] + '\n')
    logger.info("Restarting...")
    subprocess.Popen([sys.executable, '-m', 'onthespot.web'] + (sys.argv[1:]))
    os._exit(0)


@app.route('/api/download_queue')
@login_required
def get_items():
    with download_queue_lock:
        return Response(json.dumps(download_queue, sort_keys=True), mimetype='application/json')

@app.route('/api/cancel/<path:local_id>', methods=['POST'])
@login_required
def cancel_item(local_id):
    with download_queue_lock:
        if local_id in download_queue:
            download_queue[local_id]['item_status'] = 'Cancelled'
    return jsonify(success=True)


@app.route('/api/retry/<path:local_id>', methods=['POST'])
@login_required
def retry_item(local_id):
    with download_queue_lock:
        if local_id in download_queue:
            download_queue[local_id]['item_status'] = 'Waiting'
            download_queue[local_id]['available'] = True
    return jsonify(success=True)


@app.route('/api/download/<path:local_id>')
@login_required
def download_media(local_id):
    if local_id != 'logs':
        return send_file(download_queue[local_id]['file_path'], as_attachment=True)
    else:
        return send_file(os.path.join(cache_dir(), "logs", config.session_uuid, "onthespot.log"), as_attachment=True)

@app.route('/api/parse_url/<path:url>', methods=['POST'])
@login_required
def parse_download(url):
    parse_url(url)
    return jsonify(success=True)


@app.route('/api/delete/<path:local_id>', methods=['DELETE'])
@login_required
def delete_media(local_id):
    os.remove(download_queue[local_id]['file_path'])
    download_queue[local_id]['item_status'] = 'Deleted'
    return jsonify(success=True)


@app.route('/api/update_settings', methods=['POST'])
@login_required
def update_settings():
    data = request.json
    for key, value in data.items():
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        config.set(key, value)
        config.save()
    return jsonify(success=True)


@app.route('/api/add_account', methods=['POST'])
@login_required
def add_account():
    account = request.get_json()
    if account['service'] == 'apple_music':
        apple_music_add_account(account['password'])
    elif account['service'] == "bandcamp":
        bandcamp_add_account()
    elif account['service'] == "deezer":
        deezer_add_account(account['password'])
    elif account['service'] == "qobuz":
        qobuz_add_account(account['email'], account['password'])
    elif account['service'] == "soundcloud":
        soundcloud_add_account(account['password'])
    elif account['service'] == "youtube_music":
        youtube_music_add_account()
    elif account['service'] == "crunchyroll":
        crunchyroll_add_account(account['email'], account['password'])
    elif account['service'] == "generic":
        generic_add_account()
    config.set('active_account_number', config.get('active_account_number') + 1)
    config.save()
    return jsonify(success=True)


@app.route('/api/remove_account/<path:uuid>', methods=['DELETE'])
@login_required
def remove_account(uuid):
    accounts = config.get('accounts').copy()
    for i, account in enumerate(accounts):
        if account['uuid'] == uuid:
            account_number = i
    del account_pool[account_number]
    del accounts[account_number]
    config.set('accounts', accounts)
    config.set('active_account_number', 0)
    config.save()
    return jsonify(success=True)


@app.route('/api/clear_cache', methods=['DELETE'])
@login_required
def clear_cache():
    shutil.rmtree(os.path.join(cache_dir(), "reqcache"))
    shutil.rmtree(os.path.join(cache_dir(), "logs"))
    return jsonify(success=True)


# Plex API routes
@app.route('/plex_playlists')
@login_required
def plex_playlists():
    """Display the playlist import page"""
    logger.info("=== Plex playlists route accessed ===")
    if not PLEX_AVAILABLE:
        return jsonify(success=False, error="Plex API not available"), 500
    logger.debug("=== Loading Plex playlists page ===")
    config_path = os.path.join(config_dir(), 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)

    # Get m3u directory from config
    m3u_formatter = config_data.get('m3u_path_formatter', './m3u/')
    logger.debug(f"M3U formatter from config: {m3u_formatter}")

    # Remove any trailing / and filename patterns
    m3u_directory = m3u_formatter.rsplit(os.path.sep, 1)[0] if os.path.sep in m3u_formatter else m3u_formatter.rsplit('/', 1)[0] if '/' in m3u_formatter else 'M3U'
    logger.debug(f"M3U directory (relative): {m3u_directory}")

    # Expand the path to absolute path - always join with audio_download_path if it's a relative path
    if not os.path.isabs(m3u_directory):
        m3u_directory = os.path.join(config_data.get('audio_download_path', './downloads'), m3u_directory)

    logger.debug(f"M3U directory (absolute): {m3u_directory}")
    logger.debug(f"Directory exists: {os.path.exists(m3u_directory)}")

    # List all m3u files
    playlists = []
    if os.path.exists(m3u_directory):
        files = os.listdir(m3u_directory)
        logger.debug(f"Files in directory: {files}")
        for filename in files:
            if filename.lower().endswith('.m3u') or filename.lower().endswith('.m3u8'):
                full_path = os.path.join(m3u_directory, filename)
                playlists.append({
                    'name': filename,
                    'path': full_path
                })
                logger.debug(f"Added playlist: {filename} -> {full_path}")

    logger.info(f"Found {len(playlists)} playlists in {m3u_directory}")
    return render_template('plex_playlists.html', config=config_data, playlists=playlists, m3u_directory=m3u_directory)


@app.route('/api/plex/import_playlist', methods=['POST'])
@login_required
def plex_import_playlist():
    """Import a playlist to Plex"""
    logger.debug("=== Plex import playlist API called ===")
    data = request.json
    playlist_path = data.get('playlist_path')

    logger.debug(f"Received playlist path: {playlist_path}")

    if not playlist_path:
        logger.error("No playlist path provided")
        return jsonify(success=False, error='No playlist path provided')

    if not os.path.exists(playlist_path):
        logger.error(f"Playlist file not found: {playlist_path}")
        return jsonify(success=False, error='Playlist file not found')

    logger.info(f"Attempting to import playlist: {playlist_path}")
    logger.debug(f"Plex config - Server: {plex_api.server_url}, Library: {plex_api.library_section_id}, Token: {'SET' if plex_api.auth_token else 'NOT SET'}")

    result = plex_api.upload_playlist(playlist_path)
    logger.debug(f"Import result: {result}")
    return jsonify(**result)


@app.route('/api/plex/delete_playlist', methods=['DELETE'])
@login_required
def plex_delete_playlist():
    """Delete a playlist file"""
    logger.debug("=== Plex delete playlist API called ===")
    data = request.json
    playlist_path = data.get('playlist_path')

    logger.debug(f"Received playlist path to delete: {playlist_path}")

    if not playlist_path:
        logger.error("No playlist path provided")
        return jsonify(success=False, error='No playlist path provided')

    if not os.path.exists(playlist_path):
        logger.error(f"Playlist file not found: {playlist_path}")
        return jsonify(success=False, error='Playlist file not found')

    try:
        os.remove(playlist_path)
        logger.info(f"Successfully deleted playlist: {playlist_path}")
        return jsonify(success=True)
    except Exception as e:
        logger.error(f"Failed to delete playlist {playlist_path}: {str(e)}")
        return jsonify(success=False, error=str(e))


def main():
    config.migration()
    print(f'OnTheSpot Version: {config.get("version")}')
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host IP address')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    fill_account_pool = FillAccountPool()

    fill_account_pool.finished.connect(lambda: logger.info("Finished filling account pool."))
    fill_account_pool.progress.connect(lambda message, status: logger.info(f"{message} {'Success' if status else 'Failed'}"))

    fill_account_pool.start()

    thread = threading.Thread(target=parsingworker)
    thread.daemon = True
    thread.start()

    def start_workers():
        """Start all worker threads and register them"""
        logger.info("Starting worker threads...")

        for _ in range(config.get('maximum_queue_workers')):
            queue_worker = QueueWorker()
            queue_worker.start()
            register_worker(queue_worker)

        for _ in range(config.get('maximum_download_workers')):
            download_worker = DownloadWorker()
            download_worker.start()
            register_worker(download_worker)

        if config.get('enable_retry_worker'):
            retryworker = RetryWorker()
            retryworker.start()
            register_worker(retryworker)

        # Start auto-clear worker
        autoclear_worker = AutoClearWorker()
        autoclear_worker.start()
        register_worker(autoclear_worker)

        logger.info("All workers started and registered")

    def restart_workers():
        """Kill all workers and restart them - called when downloads fail repeatedly"""
        logger.warning("RESTARTING ALL WORKERS due to repeated download failures...")

        # Kill existing workers
        kill_all_workers()

        # Wait a bit for cleanup
        time.sleep(2)

        # Start fresh workers
        start_workers()

        logger.info("Worker restart complete!")

    # Register the restart callback
    set_worker_restart_callback(restart_workers)

    # Start initial workers
    start_workers()

    fill_account_pool.wait()

    if config.get('mirror_spotify_playback'):
        mirrorplayback = MirrorSpotifyPlayback()
        mirrorplayback.start()

    cached_file_path = os.path.join(cache_dir(), 'cached_download_queue.txt')
    if os.path.isfile(cached_file_path):
        logger.info(f'Found cached download queue at {cached_file_path}, appending items to download queue...')
        get_search_results(cached_file_path)
        os.remove(cached_file_path)

    # Log registered routes for debugging
    logger.info("=== Registered Routes ===")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule.rule} -> {rule.endpoint}")
    logger.info("========================")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
