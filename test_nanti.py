from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load model & tokenizer sekali saja saat server start
MODEL_DIR = "./saved_models/IndoBERT_version1/32_2e-5"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

app = FastAPI()

class InputText(BaseModel):
    text: str

@app.post("/predict")
def predict(input_data: InputText):
    inputs = tokenizer(input_data.text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()
    return {
        "label": pred,
        "probabilities": probs.tolist()
    }
