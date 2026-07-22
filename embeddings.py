from sentence_transformers import SentenceTransformer
from config import EMBED_MODEL_NAME

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def embed_text(text: str):
    model = get_model()
    return model.encode(text).tolist()
