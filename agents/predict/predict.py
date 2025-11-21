import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
from dotenv import load_dotenv

load_dotenv()

MODEL_DIR = os.getenv("MODEL_DIR")
if not MODEL_DIR:
    raise ValueError("❌ MODEL_DIR tidak ditemukan di file .env")

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

def classify_berita(title, content):
    text = f"{title}\n\n{content}"
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()

    label = "valid" if pred == 1 else "hoaks"
    confidence = round(probs[0][pred].item() * 100, 2)
    return {"label": label, "confidence": confidence, "probs": probs.tolist()}

