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
import psycopg2

load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
client = genai.Client(api_key=API_KEY)
db = psycopg2.connect(DATABASE_URL)

""" TABLE SCHEMA:
    dish_name: str
    ingredients: jsonb Ex. (Json({"main": ["shrimp", "pasta"],"sauce": ["garlic", "olive oil", "red pepper flakes"],"extras": ["parsley", "lemon juice"]}))
    calories: int
    protein: int
    carbs: int
    fat: int
    created_at: timestamptz
"""

# processor = AutoImageProcessor.from_pretrained("nateraw/food")
# model = AutoModelForImageClassification.from_pretrained("nateraw/food")
# pipeline = pipeline("image-classification", model="nateraw/food")
# segments = pipeline("https://images.unsplash.com/photo-1511688878353-3a2f5be94cd7") # Insert image here
# print(f"First label: {segments[0]["label"]}")
# print(f"Second label: {segments[1]["label"]}")
# print(f"Third label: {segments[2]["label"]}")

# while True:
#     selection = input("Select from the food items below that best matches your image:\n"+
#              f"0: {segments[0]["label"]}\t1: {segments[1]["label"]}\t2:{segments[2]["label"]}\n>")
#     if selection in "012":
#         break

# Store all images in the images file
image_extensions = ['.jpg', '.jpeg', '.png']
image_files = [f for f in os.listdir('images') if os.path.splitext(f.lower())[1] in image_extensions]

if not image_files:
    raise Exception

# Prepare images for prompt using the the Files API
uploaded_files = []
for filename in image_files:
    filepath = os.path.join('images', filename)
    uploaded_file = client.files.upload(file=filepath)
    uploaded_files.append(uploaded_file)

response = client.models.generate_content(
    model='gemini-2.5-flash',
    config=types.GenerateContentConfig(
        system_instruction=("You are a helpful AI assistant that identifies ingredients and food from images."
                            "Only output the names of ingredients or food, separated by commas. Leave no spaces immediately after a comma."
                            "The first letter of an element should be capitalized."
                            "List the identified ingredients and food contained within the input."),
                            max_output_tokens=600
    ),
    contents=[uploaded_files]
)

# food = segments[int(selection)]["label"]
# response = client.models.generate_content(
#     model="gemini-2.5-flash",
#     config=types.GenerateContentConfig(
#         system_instruction=("You are a helpful AI assistant that provides recipe suggestions from food."
#                             "Only output the names of ingredients, separated by commas. Leave no spaces immediately after a comma."
#                             "The first letter of an element should be capitalized."
#                             "List the most likely ingredients contained within the input text."),
#                             max_output_tokens=600
#     ),
#     contents=food
# )

# [Ingredient1,Ingredient2,...]
ingredients = response.text.split(",")
print(ingredients)

print(f"Detected ingredients: {", ".join(ingredients)}")
print("Please input more ingredients if needed. (n to end)")

# TODO: Add removal function
# User inputs more ingredients
while True:
    ing = input(">")
    if ing.lower() == "n":
        break
    if ing:
        ing = ing.strip()
        ingredients.append(ing)
    

print(f"Resulting ingredients: {", ".join(ingredients)}")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction=("You are a helpful AI assistant that provides recipe suggestions from food."
                            "List the inferred nutritional value given the food and its ingredients from the input string, separated by commas."
                            "Each element in the list of nutritional values should follow the form: '<nutritional element>: <numerical value>'"
                            "Suggest up to 5 improvements to the recipe to make the food and using the list of ingredients from the input string."
                            "Keep each recipe suggestion to at most 3 sentences. Do not make up ingredients not included in the input string."
                            "Additionally, suggest 1 alternate recipe suggestions either similar to the given food item or using the same ingredients."
                            "Provide a descriptive 1-sentence description for the alternate recipe followed by the list of ingredients."
                            "Also list nutritional values in the same format as the first recipe, followed by step-by-step instructions on how to make the alternate food item."),
    ),
    contents=f"Food: {ingredients}\nIngredients: " + ", ".join(ingredients)
)

# TODO: Edit the prompt to additionally output something that follows the schema of the table
# TODO: Parse the response, and insert into the table. A sample insert query is below.
cur = db.cursor()
cur.execute("INSERT INTO recipes (dish_name, calories) VALUES (%s, %s)",("Tacos", 600))
db.commit()
cur.close()
db.close()

print(response.text)