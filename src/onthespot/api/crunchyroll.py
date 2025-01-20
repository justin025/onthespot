from hashlib import md5
import json
import os
import uuid
import requests
import crunpyroll
from yt_dlp import YoutubeDL
from pywidevine.cdm import Cdm
from pywidevine.pssh import PSSH
from pywidevine.device import Device
from ..constants import WVN_KEY
from ..otsconfig import config
from ..runtimedata import get_logger, account_pool


logger = get_logger("api.crunchyroll")


def crunchyroll_login_user(account):
    logger.info('Logging into Crunchyroll account...')
    try:
        # Ping to verify connectivity
        requests.get('https://www.crunchyroll.com')
        client = crunpyroll.Client(
            email=account['login']['email'],
            password=account['login']['password'],
            device_id=account['uuid'],
            device_name='OnTheSpot',
            preferred_audio_language=config.get("preferred_audio_language"),
            locale="en-US"

        )
        client.start()
        account_pool.append({
            "uuid": account['uuid'],
            "username": account['login']['email'],
            "service": "crunchyroll",
            "status": "active",
            "account_type": "premium",
            "bitrate": "1080p",
            "login": {
                "email": account['login']['email'],
                "password": account['login']['password'],
                "session": client
            }
        })
        return True
    except Exception as e:
        logger.error(f"Unknown Exception: {str(e)}")
        account_pool.append({
            "uuid": account['uuid'],
            "username": account['login']['email'],
            "service": "crunchyroll",
            "status": "error",
            "account_type": "N/A",
            "bitrate": "N/A",
            "login": {
                "email": account['login']['email'],
                "password": account['login']['password'],
                "session": None
            }
        })
        return False


def crunchyroll_add_account(email, password):
    cfg_copy = config.get('accounts').copy()
    new_user = {
            "uuid": str(uuid.uuid4()),
            "service": "crunchyroll",
            "active": True,
            "login": {
                "email": email,
                "password": password
            }
        }
    cfg_copy.append(new_user)
    config.set('accounts', cfg_copy)
    config.update()


def crunchyroll_get_token(parsing_index):
    return account_pool[parsing_index]['login']


def crunchyroll_get_search_results(token, search_term, _):
    search_data = token['session'].search(search_term)
    results = json.loads(str(search_data))['items']

    search_results = []
    for result in results:
        try:
            thumbnail_url = result.get('images', {}).get('thumbnail', [])[0].get('url')
        except Exception:
            thumbnail_url = result.get('images', {}).get('poster_wide', [])[0].get('url')

        if result.get('episode_number'):
            item_type = 'episode'
            item_url = f"https://crunchyroll.com/watch/{result.get('id')}/{result.get('slug')}"
        else:
            item_type = 'show'
            item_url = f"https://crunchyroll.com/series/{result.get('id')}/{result.get('slug')}"

        search_results.append({
            'item_id': f"{result.get('id')}/{result.get('slug')}",
            'item_name': result['title'],
            'item_by': 'Crunchyroll',
            'item_type': item_type,
            'item_service': "crunchyroll",
            'item_url': item_url,
            'item_thumbnail_url': thumbnail_url
        })

    logger.debug(search_results)
    return search_results


def crunchyroll_get_episode_metadata(token, item_id):
    url = f'https://crunchyroll.com/watch/{item_id}'
    request_key = md5(f'{url}'.encode()).hexdigest()
    cache_dir = os.path.join(config.get('_cache_dir'), 'reqcache')
    os.makedirs(cache_dir, exist_ok=True)
    req_cache_file = os.path.join(cache_dir, request_key + '.json')

    if os.path.isfile(req_cache_file):
        logger.debug(f'URL "{url}" cache found ! HASH: {request_key}')
        with open(req_cache_file, 'r', encoding='utf-8') as cf:
            info_dict = json.load(cf)

    else:
        ydl_opts = {}
        ydl_opts['quiet'] = True
        ydl_opts['allow_unplayable_formats'] = True
        ydl_opts['username'] = token['email']
        ydl_opts['password'] = token['password']

        info_dict = YoutubeDL(ydl_opts).extract_info(url, download=False)
        json_output = json.dumps(info_dict, indent=4)
        with open(req_cache_file, 'w', encoding='utf-8') as cf:
            cf.write(json_output)

    subtitle_urls = {}
    for key, item in info_dict.get('subtitles').items():
        subtitle_urls[key] = {"url": item[0].get("url"), "ext": item[0].get("ext")}

    info = {}
    info['title'] = info_dict.get('episode')
    info['description'] = info_dict.get('description')
    info['image_url'] = info_dict.get('thumbnail')
    info['show_name'] = info_dict.get('series')
    info['season_number'] = info_dict.get('season_number')
    info['episode_number'] = info_dict.get('episode_number')
    info['subtitle_urls'] = subtitle_urls
    info['item_url'] = info_dict.get('webpage_url')
    info['release_year'] = info_dict.get('release_year') if info_dict.get('release_year') else info_dict.get('upload_date')[:4]
    info['is_playable'] = True
    info['item_id'] = info_dict.get('id')
    info['explicit'] = True if info_dict.get('age_limit') == 17 else False

    return info


def crunchyroll_get_show_episode_ids(token, show_id):
    show_id = show_id.split('/')[0]
    episode_ids = []

    resp = token['session'].get_seasons(show_id)
    show_data = json.loads(str(resp))
    for season in show_data['items']:

        resp = token['session'].get_episodes(season.get('id'))
        season_data = json.loads(str(resp))

        for episode in season_data.get('items', []):
            episode_ids.append(f"{episode.get('id')}/{episode.get('slug')}")

    return episode_ids

def crunchyroll_get_decryption_key(token, item_id):
    cdm = Cdm.from_device(Device.loads(WVN_KEY))

    streams = token['session'].get_streams(item_id.split("/")[0])
    manifest = token['session'].get_manifest(streams.url)

    pssh = PSSH(manifest.content_protection.widevine.pssh)
    session_id = cdm.open()
    challenge = cdm.get_license_challenge(session_id, pssh)
    wvn_license = token['session'].get_license(
        streams.media_id,
        challenge=challenge,
        token=streams.token
    )
    cdm.parse_license(session_id, wvn_license)
    for key in cdm.get_keys(session_id, "CONTENT"):
        decryption_key = key.key.hex()
    cdm.close(session_id)

    token['session'].delete_active_stream(
        streams.media_id,
        token=streams.token
    )
    return decryption_key
