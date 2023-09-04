from urllib.parse import urlparse


def looks_like_player_id(text):
    return text.isalnum() and len(text) in (11, 12, 13)


def try_parse_game_url(text):
    try:
        parsed = urlparse(text)
        if parsed:
            assert parsed.path == "/spectator"
            assert parsed.query.startswith('id=')
            return parsed.netloc, parsed.query.split('=')[-1]
    except:
        pass


def build_api_url(host, page, id):
    return "http://{}/api/{}?id={}".format(host, page, id)
