from transformers import AutoImageProcessor, AutoModelForImageClassification
from transformers import pipeline
from transformers import CLIPProcessor,CLIPModel
from PIL import Image
import requests
import torch
from openai import OpenAI
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

# processor = AutoImageProcessor.from_pretrained("nateraw/food")
# model = AutoModelForImageClassification.from_pretrained("nateraw/food")
# pipeline = pipeline("image-classification", model="nateraw/food")
# segments = pipeline("https://images.unsplash.com/photo-1511688878353-3a2f5be94cd7") # Insert image here
# print(f"First label: {segments[0]["label"]}")
# print(f"Second label: {segments[1]["label"]}")

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
url = "https://images.unsplash.com/photo-1511688878353-3a2f5be94cd7" #Insert image URL here
image = Image.open(requests.get(url, stream=True).raw)
labels = ["pizza", "burger", "sushi", "salad", "pasta"]
inputs = processor(text=labels, images=image, return_tensors="pt", padding=True)

with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits_per_image
    probs = logits.softmax(dim=1)
predicted_label = probs.argmax().item()
print(labels[predicted_label])
# ingredients = ["dough", "cheese", "tomato sauce", "rice", "seaweed", "avocado", "lettuce",
#                "bacon", "beef", "chicken", "pasta", "olive oil"]
#prompt = f"Given the food item {labels[predicted_label]}, list the ingredients that are likely to be in it from the list: {', '.join(ingredients)}. Suggest enhancements and substitutions for the ingredients to improve the dish."
prompt = f"Given the food item {labels[predicted_label]}, list the ingredients that are likely to be in it and suggest enhancements and substitutions for the ingredients to improve the dish."

# ChatGPT Implementation
# client = OpenAI(api_key="your api key here")
# response = client.chat.completions.create(
#     model="gpt-4",
#     messages=[
#         {"role": "system", "content": "You are a helpful AI assistant that provides information and suggestions about food and recipes."},
#         {"role": "user", "content": prompt}
#     ]
# )
# print(response.choices[0].message.content)

# Gemini Implementation
load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")
client = genai.Client(api_key=API_KEY)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    config=types.GenerateContentConfig(
        system_instruction="You are a helpful AI assistant that provides information and suggestions about food and recipes.",
    ),
    contents=prompt
)
print(response.text)