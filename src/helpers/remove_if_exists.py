import os


def remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)