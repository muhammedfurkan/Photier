from abc import ABCMeta
from urllib import request
from urllib.parse import urlparse
import os
import face_recognition
import numpy as np
from database import get_db
from utils.headers import HEADERS


class Model(metaclass=ABCMeta):
    __table__ = "model"

    def __init__(self, id=None, *args, **kwargs):
        self.id = id


class Face(Model):
    __table__ = 'faces'

    def __init__(self, location=None, encode=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encode = encode
        self.location = location

    def save_to_db(self):
        all_faces = self.get_all()
        encodes = [np.array(face.encode) for face in all_faces]
        if encodes:
            has_id = any(
                face_recognition.compare_faces(encodes, np.array(self.encode)))
            if has_id is True:
                print(f'[!] this face has id in database.')
                return
            else:
                print(f'[+] saving new face id to database.')
                db = get_db()
                cursor = db.cursor()
                cursor.execute(
                    f"""INSERT INTO face (location,encode) VALUES (?,?)""",
                    [str(self.location), str(self.encode)])

                db.commit()
        else:
            print(f'[+] saving new face id to database.')
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                f"""INSERT INTO face (location,encode) VALUES (?,?)""",
                [str(self.location), str(self.encode)])
            db.commit()

    @classmethod
    def get_all(cls):
        db = get_db()
        cursor = db.cursor()
        records = cursor.execute(f"SELECT * FROM face;").fetchall()
        return [
            cls(location=eval(record[1]), encode=eval(record[2]))
            for record in records
        ]

    def to_json(self):
        return {
            'location': self.location,
            'encode': self.encode,
        }


class Photo(Model):
    __table__ = 'photos'

    def __init__(self, url, locations=None, encodes=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.locations = locations
        self.encodes = encodes

    @property
    def faces(self):
        self.get_faces()
        records = [{
            'location': i[0],
            'encode': i[1]
        } for i in zip(self.locations, self.encodes)]
        return [Face(**record) for record in records]

    @property
    def faces_count(self):
        return len(self.faces)

    def to_json(self):
        return {
            'url': self.url,
            'faces': [face.to_json() for face in self.faces],
            'faces_count': self.faces_count
        }

    def get_faces(self):
        extention = os.path.splitext(urlparse(self.url).path)[1]
        print(extention)
        if extention in ['.jpg', '.png', '.jpeg']:
            req = request.Request(url=self.url, headers=HEADERS)
            img = request.urlopen(url=req)
            self.img_fc = face_recognition.load_image_file(img)
            self.locations = [
                list(i) for i in face_recognition.face_locations(self.img_fc)
            ]
            self.encodes = [
                list(i) for i in face_recognition.face_encodings(self.img_fc)
            ]
        else:
            raise Exception('[!] image url must extention be in (jpg,png,jpeg).')

    def save_to_db(self):
        if Photo.get_one_by_url(self.url):
            raise ValueError('[!] this image is in database')
        if self.faces_count < 1:
            raise ValueError('[!] image must contain one face at less')
        # get photo faces
        for face in self.faces:
            face.save_to_db()
        print(f'[+] saving photo to database.')
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f"""INSERT INTO photo (url,locations,encodes) VALUES (?,?,?)""",
                       [self.url, str(self.locations), str(self.encodes)])
        db.commit()

    def is_similar(self, other: "Photo"):
        self_encode = np.array(self.encodes)
        encodes_list = [np.array(encode) for encode in eval(other.encodes)]
        data = []
        for encode in encodes_list:
            try:
                result = any(face_recognition.compare_faces(encode, self_encode))
                data.append(result)
            except Exception as e:
                print(str(e))
            finally:
                continue
        return any(data)

    @classmethod
    def get_one_by_url(cls, url):
        db = get_db()
        cursor = db.cursor()
        record = cursor.execute("SELECT * FROM photo WHERE url = (?)",
                                [url]).fetchone()
        if record:
            return cls(url=record[1], locations=record[2], encodes=record[3])

    @classmethod
    def get_one_by_id(cls, id):
        db = get_db()
        cursor = db.cursor()
        record = cursor.execute(
            "SELECT * FROM photo WHERE id = (?)", [id, ]).fetchone()
        return cls(id=record[0], url=record[1], locations=record[2], encodes=record[3])

    @classmethod
    def get_all(cls):
        db = get_db()
        cursor = db.cursor()
        records = cursor.execute("SELECT * FROM photo;").fetchall()
        return [cls(id=record[0], url=record[1], locations=eval(record[2]), encodes=eval(record[3])) for record in
                records]

    @classmethod
    def get_similar_by_id(cls, id):
        p1 = cls.get_one_by_id(id=id)
        similar = []
        for p in Photo.get_all():
            if p.is_similar(p1):
                similar.append(p)
        return similar

    @classmethod
    def get_similar_by_url(cls, url):
        p1 = Photo(url=url)
        p1.get_faces()
        similar = []
        for p in Photo.get_all():
            encodes_list = [np.array(encode) for encode in p.encodes]
            result = any(face_recognition.compare_faces(
                encodes_list, np.array(p1.encodes)))
            if result is True:
                similar.append(p)

        return similar
