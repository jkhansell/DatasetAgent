import torch
from sentence_transformers import SentenceTransformer

def get_embedder():
    
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_id = "google/embeddinggemma-300M"
    model = SentenceTransformer(model_id).to(device=device)

    return model