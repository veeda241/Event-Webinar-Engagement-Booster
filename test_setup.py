from transformers import pipeline
from fastapi import FastAPI
import torch
import sqlalchemy

def test_environment():
    print("Testing environment setup:")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    # Test transformers
    generator = pipeline('text-generation', model='distilgpt2')
    print("Transformers pipeline created successfully")
    
    return "Environment setup complete!"

if __name__ == "__main__":
    test_environment()