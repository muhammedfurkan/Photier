import os
import requests
from dotenv import load_dotenv
from config import Config
from photier.models import Photo
from .headers import HEADERS

load_dotenv(dotenv_path=Config.ENV)


def get_new_urls():
    """
    get just new added images urls by sending request to all images endpoint
    :return: list of urls
    """
    HEADERS.update({'authorization': os.environ.get("API_TOKEN")})
    try:
        req = requests.get('https://teklas-api.iciletisim.app/api/posts/all-images', headers=HEADERS)
        req.raise_for_status()
        (result, _) = req.json().values()
        items = [item.get('media') for item in result]
        saved_photo_urls = {photo.url for photo in Photo.get_all()}
        endpoint_urls = []
        for item in items:
            endpoint_urls.extend(image_obj['url'] for image_obj in item)
        return set(endpoint_urls).difference(saved_photo_urls)
    except Exception as e:
        return str(e)


