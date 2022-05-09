import logging
import os
from flask import Flask, make_response, jsonify, request
from flask_cors import CORS

from config import Config
from database import create_db
from photier.models import Photo
from functools import wraps
from dotenv import load_dotenv
from utils.utils import get_new_urls
from flask_apscheduler import APScheduler

logging.basicConfig(filename='photier.txt',
                    filemode='w',
                    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(name='photier')

app = Flask(__name__)
app.config.from_object(Config)
CORS(app=app)
load_dotenv(dotenv_path='.env')
scheduler = APScheduler(app=app)
TOKEN = os.environ.get('TOKEN')


def token_required(func):
    @wraps(func)
    def decorated_fun(*args, **kwargs):
        req = request.args
        token = req.get('token', None)
        if token == TOKEN:
            return func(*args, **kwargs)
        else:
            response = {
                'unauthenticated': 'check token please before continue!'}
            return make_response(make_response(response))

    return decorated_fun


@app.before_first_request
def before_first_request():
    create_db()


@app.route('/')
def index():
    populate_database()
    return {'page': 'index'}


@app.route('/api/v1/get-all')
@token_required
def get_all():
    try:
        all_photos = Photo.get_all()
        response = [{'id': photo.id, 'url': photo.url} for photo in all_photos]
        return make_response(jsonify(response)), 200
    except Exception as e:
        response = {'error': str(e)}
        logging.debug(msg=str(e))
        return make_response(response), 404


@app.route('/api/v1/get-one/<photo_id>')
@token_required
def get_one(photo_id):
    try:
        photo = Photo.get_one_by_id(id=int(photo_id))
        if photo:
            similar = Photo.get_similar_by_id(photo_id)
            response = {'id': photo.id,
                        'url': photo.url,
                        'similar': [{'id': p.id, 'url': p.url} for p in similar]}
            return make_response(jsonify(response)), 200
        else:
            response = {'error': 'this id is not exists'}
            return make_response(jsonify(response)), 404
    except Exception as e:
        response = {'error': str(e)}
        logging.debug(msg=str(e))
        return make_response(response), 404


@app.route('/api/v1/get-similar')
@token_required
def get_similar():
    try:
        req = request.args
        url = req.get('url', None)
        if url:
            similar = Photo.get_similar_by_url(url=url)
            print(similar)
            response = {'url': url,
                        'similar': [{'id': p.id, 'url': p.url} for p in similar]}
            return make_response(jsonify(response)), 200
    except Exception as e:
        response = {'error': str(e)}
        logging.debug(msg=str(e))
        return make_response(response), 404


@app.route('/api/v1/get-similar', methods=['POST'])
@token_required
def create_one():
    try:
        req = request.args
        url = req.get('url', None)
        if url:
            p = Photo(url=url)
            p.get_faces()
            p.save_to_db()
            response = {'new_photo': p.to_json()}
            return make_response(jsonify(response)), 200
    except Exception as e:
        response = {'error': str(e)}
        logging.debug(msg=str(e))
        return make_response(response), 404
    return "All photos"


def insert_list(images_list):
    """
    used to insert list of images urls to database
    :param images_list: urls list
    :return: None
    """
    count = 0
    for url in images_list:
        try:
            if Photo.get_one_by_url(url=url):
                continue
            p = Photo(url=url)
            p.get_faces()
            p.save_to_db()
            count += 1
        except Exception as e:
            print(str(e))
        finally:
            continue
    return count


@scheduler.task(id='populate_photier', trigger='cron', minute=0, hour=0, day="*")
def populate_database():
    """
    this function will run automatically at 00:00 every day
    :return:
    """
    images_urls = list(get_new_urls())
    try:
        insert_list(images_urls)
        logger.info(msg='populating started')
    except Exception as e:
        logging.debug(str(e))


if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True,port=5000)
