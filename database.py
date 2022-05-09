import sqlite3

from config import Config



def create_db():
    """
    create database
    :return: None
    """
    connection = sqlite3.connect(Config.DATABASE)
    cursor = connection.cursor()
    with open('schema.sql', 'r') as f:
        cursor.executescript(f.read())


def get_db():
    """
    get connection to database
    :return: sqlite3 connection object
    """
    connection = sqlite3.connect(Config.DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


