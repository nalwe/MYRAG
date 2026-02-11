import faiss
import numpy as np
import os

EMBED_SIZE = 1536

def create_index():
    return faiss.IndexFlatL2(EMBED_SIZE)

def save_index(index, path):
    faiss.write_index(index, path)

def load_index(path):
    return faiss.read_index(path)
