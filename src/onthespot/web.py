import os
# Required for librespot-python
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
import argparse
import json
import threading
import time
import traceback
from flask import Flask, jsonify, render_template, redirect, request, send_file, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from .accounts import FillAccountPool, get_account_token
from .api.apple_music import apple_music_get_track_metadata
from .api.bandcamp import bandcamp_get_track_metadata
from .api.deezer import deezer_get_track_metadata, deezer_add_account
from .api.qobuz import qobuz_get_track_metadata
from .api.soundcloud import soundcloud_get_track_metadata
from .api.spotify import MirrorSpotifyPlayback, spotify_new_session, spotify_get_track_metadata, spotify_get_podcast_episode_metadata
from .api.tidal import tidal_get_track_metadata
from .api.youtube_music import youtube_music_get_track_metadata
from .api.crunchyroll import crunchyroll_get_episode_metadata
from .downloader import DownloadWorker, RetryWorker
from .otsconfig import config_dir, config
from .parse_item import parsingworker, parse_url
from .runtimedata import get_logger, account_pool, pending, download_queue, download_queue_lock, pending_lock, download_workers, queue_workers
from .search import get_search_results

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

    def run(self):
        while True:
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
                                'item_thumbnail': item_metadata["image_url"],
                                'item_url': item_metadata["item_url"]
                            }
                else:
                    time.sleep(0.2)
            except Exception as e:
                logger.error(f"Unknown Exception for {item}: {str(e)}\nTraceback: {traceback.format_exc()}")
                with pending_lock:
                    pending[local_id] = item

class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


login_manager.login_view = "login"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not config.get('use_webui_login') or not config.get('webui_username'):
        user = User('guest')
        login_user(user)
        return redirect(url_for('download_queue_page'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == config.get('webui_username') and password == config.get('webui_password'):
            user = User(username)
            login_user(user)
            return redirect(url_for('download_queue_page'))
        flash('Invalid credentials, please try again.')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/items')
@login_required
def get_items():
    with download_queue_lock:
        return jsonify(download_queue)


@app.route('/icons/<path:filename>')
def serve_icons(filename):
    icon_path = os.path.join(config.app_root, 'resources', 'icons', filename)
    return send_file(icon_path)


@app.route('/download/<path:local_id>')
@login_required
def download_media(local_id):
    return send_file(download_queue[local_id]['file_path'], as_attachment=True)


@app.route('/delete/<path:local_id>', methods=['DELETE'])
@login_required
def delete_media(local_id):
    os.remove(download_queue[local_id]['file_path'])
    download_queue[local_id]['item_status'] = 'Deleted'
    return jsonify(success=True)


@app.route('/cancel/<path:local_id>', methods=['POST'])
@login_required
def cancel_item(local_id):
    download_queue[local_id]['item_status'] = 'Cancelled'
    return jsonify(success=True)


@app.route('/retry/<path:local_id>', methods=['POST'])
@login_required
def retry_item(local_id):
    download_queue[local_id]['item_status'] = 'Waiting'
    return jsonify(success=True)


@app.route('/download/<path:url>', methods=['POST'])
@login_required
def download_file(url):
    parse_url(url)
    return jsonify(success=True)


@app.route('/clear', methods=['POST'])
@login_required
def clear_items():
    keys_to_delete = []

    for local_id, item in download_queue.items():
        if item["item_status"] == "Downloaded" or \
           item["item_status"] == "Already Exists" or \
           item["item_status"] == "Cancelled" or \
           item["item_status"] == "Deleted":
            keys_to_delete.append(local_id)
    for key in keys_to_delete:
        del download_queue[key]
    return jsonify(success=True)


@app.route('/restart_workers', methods=['POST'])
@login_required
def restart_workers():
    for download_worker in download_workers:
        download_worker.stop()

    download_workers.clear()

    item_urls = []
    for key, value in download_queue.items():
        item_urls.append(value.get('item_url'))

    with download_queue_lock:
        download_queue.clear()

    for url in item_urls:
        parse_url(url)

    for i in range(config.get('maximum_download_workers')):
        download_worker = DownloadWorker()
        download_worker.start()
        download_workers.append(download_worker)

    return jsonify(success=True)


@app.route('/download_queue')
@login_required
def download_queue_page():
    config_path = os.path.join(config_dir(), 'onthespot', 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('download_queue.html', config=config_data)


@app.route('/')
@login_required
def index():
    return redirect(url_for('download_queue_page'))


@app.route('/search')
@login_required
def search():
    config_path = os.path.join(config_dir(), 'onthespot', 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('search.html', config=config_data)


@app.route('/about')
@login_required
def about():
    return render_template('about.html')


@app.route('/search_results')
@login_required
def search_results():
    query = request.args.get('q')

    content_types = []
    if config.get('enable_search_tracks'):
        content_types.append('track')
    if config.get('enable_search_playlists'):
        content_types.append('playlist')
    if config.get('enable_search_albums'):
        content_types.append('album')
    if config.get('enable_search_artists'):
        content_types.append('artist')
    if config.get('enable_search_podcasts'):
        content_types.append('show')
    if config.get('enable_search_episodes'):
        content_types.append('episode')
    if config.get('enable_search_audiobooks'):
        content_types.append('audiobook')

    results = get_search_results(query, content_types=content_types)
    return jsonify(results)


@app.route('/settings')
@login_required
def settings():
    config_path = os.path.join(config_dir(), 'onthespot', 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('settings.html', config=config_data, account_pool=account_pool)  # Render the settings.html file


@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    data = request.json
    for key, value in data.items():
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        config.set(key, value)
        config.update()
    return jsonify(success=True)


def main():
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

    for _ in range(config.get('maximum_queue_workers')):
        queue_worker = QueueWorker()
        queue_worker.start()
        queue_workers.append(queue_worker)

    for _ in range(config.get('maximum_download_workers')):
        download_worker = DownloadWorker()
        download_worker.start()
        download_workers.append(download_worker)

    if config.get('enable_retry_worker'):
        retryworker = RetryWorker()
        retryworker.start()

    fill_account_pool.wait()

    if config.get('mirror_spotify_playback'):
        mirrorplayback = MirrorSpotifyPlayback()
        mirrorplayback.start()

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
