from config import HOST


def looks_like_player_id(text):
    return text.isalnum() and len(text) in (12, 13)


def build_api_url(page, id):
    return "http://{}/api/{}?id={}".format(HOST, page, id)
