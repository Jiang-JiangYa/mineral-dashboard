"""可离线启动的可重复基线；可选真正的多语义模型，两者不能混用索引。"""

import hashlib
import math
import struct
from collections import Counter

from .text import tokens


class Encoder:
    def __init__(self, settings):
        self.backend = settings.embedding_backend
        self.model = None
        if self.backend == "hash":
            self.dimension = 384
            self.signature = "hash-blake2b-alias-v1:384"
        elif self.backend == "sentence-transformers":
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(settings.embedding_model)
            self.dimension = self.model.get_sentence_embedding_dimension()
            self.signature = f"sentence-transformers:{settings.embedding_model}:{self.dimension}"
        else:
            raise ValueError("EMBEDDING_BACKEND 必须为 hash 或 sentence-transformers")

    def encode(self, text, query=False):
        if self.model is not None:
            prefix = "query: " if query else "passage: "
            return self.model.encode(prefix + text, normalize_embeddings=True).tolist()
        vector = [0.0] * self.dimension
        for token, count in Counter(tokens(text)).items():
            value = hashlib.blake2b(token.encode(), digest_size=8).digest()
            index = int.from_bytes(value[:4], "little") % self.dimension
            sign = 1 if value[4] & 1 else -1
            vector[index] += sign * (1 + math.log(count))
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            vector[0] = norm = 1.0
        return [value / norm for value in vector]

    def blob(self, text, query=False):
        vector = self.encode(text, query)
        return struct.pack(f"{len(vector)}f", *vector)
