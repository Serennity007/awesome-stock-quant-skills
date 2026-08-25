import os
from time import time
from define import BASE_URL
import config
import requests
from logger import log
class TrackLogger:
    def __init__(self, file_path):
        self.logger_file = file_path
        self.f = open(file_path, mode="a", encoding="utf-8")
    
    def write(self, message:str):
        self.f.write(f"{message}\n")
        self.f.flush()
