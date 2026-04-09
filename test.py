from transformers import AutoImageProcessor, AutoModelForImageClassification
from transformers import pipeline

processor = AutoImageProcessor.from_pretrained("nateraw/food")
model = AutoModelForImageClassification.from_pretrained("nateraw/food")
pipeline = pipeline("image-classification", model="nateraw/food")
segments = pipeline("") # Insert image here
print(f"First label: {segments[0]["label"]}")
print(f"Second label: {segments[1]["label"]}")