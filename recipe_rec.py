from random import choice

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
import json
import ast


load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
client = genai.Client(api_key=API_KEY)

""" TABLE SCHEMA:
    dish_name: str
    ingredients: jsonb Ex. (Json({"main": ["shrimp", "pasta"],"sauce": ["garlic", "olive oil", "red pepper flakes"],"extras": ["parsley", "lemon juice"]}))
    calories: int
    protein: int
    carbs: int
    fat: int
    created_at: timestamptz
"""

#TODO: get the nutritional value so far during the day


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



def daily_total(db):
    cur = db.cursor()
    cur.execute("SELECT COALESCE(SUM(calories), 0), COALESCE(SUM(protein), 0), COALESCE(SUM(carbs), 0), COALESCE(SUM(fat), 0) FROM recipes WHERE DATE(created_at) = CURRENT_DATE")
    result = cur.fetchone()
    cur.close()
    return result

def print_daily_total(result):
    print("Today's total nutritional values:\n")
    print(f"Calories: {result[0]}")
    print(f"Protein: {result[1]}g")
    print(f"Carbs: {result[2]}g")
    print(f"Fat: {result[3]}g\n")

def main():
    db = psycopg2.connect(DATABASE_URL, sslmode='require')
    print_daily_total(daily_total(db))
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
                                "List the identified ingredients and food contained within the input."
                                "If you cannot identify any food or ingredients, return 'N/A'"),
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
    # print(ingredients)
    if 'N/A' in ingredients and len(ingredients) == 1:
        print("No ingredients detected. Please try again with different images.")
        return

    print(f"Detected ingredients: {', '.join(ingredients)}")
    print("Please input more ingredients if needed. (n to end)")

    # User inputs more ingredients
    while True:
        # ing = input(">")
        # if ing.lower() == "n":
        #     break
        # if ing:
        #     ing = ing.strip()
        #     ingredients.append(ing)

        # print("Ingredients: ")
        # for cat, i in enumerate(ingredients):
        #     print(f'{cat}: ')
        #     for ing in i:
        #         print(f'\t{ing}')
        
        print("Options:\n1. Add ingredient\n2. Remove ingredient\n3. Finish")
        option = input(">").strip()
        if option == "1":
            new_ing = input("Enter ingredient to add: ").strip()
            if new_ing:
                ingredients.append(new_ing)
        elif option == "2":
            remove = input("Enter ingredient to remove: ").strip()
            if remove in ingredients:
                ingredients.remove(remove)
        elif option == "3":
            break

    print(f"Resulting ingredients: {', '.join(ingredients)}")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=("You are a helpful AI assistant that provides recipe suggestions from food."
                                # "Suggest up to 5 improvements to the recipe to make the food and using the list of ingredients from the input string."
                                # "Keep each recipe suggestion to at most 3 sentences."
                                "Suggest 3 alternate recipe suggestions either similar to the given food item or using the same ingredients."
                                "For each recipe, list the inferred nutritional values, separated by commas."
                                "Each element in the list of nutritional values should follow the form: '<nutritional element>: <numerical value>'"
                                "Nutritional values should be listed in this order: Calories, Protein, Carbs, Fat"
                                "Provide a descriptive 1-sentence description for each alternate recipe followed by the list of ingredients."
                                "Then state the by step-by-step instructions on how to make them."
                                "Do not make up ingredients not included in the input string."
                                "At the very end, list valid JSON for each recipe, including nutritional values, with no code block or extra explanations."
                                "JSON schema: {'dish_name': '...', 'ingredients': '[...]', 'calories': '...', 'protein': '...', 'carbs': '...', 'fat': '...'}"),
        ),
        contents=f"Food: {ingredients}\nIngredients: " + ", ".join(ingredients)
    )

    parsed_recipes = []


    for line in response.text.splitlines():
        line = line.strip()

        if not line.startswith("{"):
            print(line)

        if line.startswith("{") and line.endswith("}"):
            try:
                recipe = ast.literal_eval(line)
                parsed_recipes.append(recipe)
            except:
                print("Parse error:", line)

    # TODO: Edit the prompt to additionally output something that follows the schema of the table
    # TODO: Parse the response, and insert into the table. A sample insert query is below.

#choose only one recipe to add to db

    print("\n--- Recipe Choices ---\n")
    for i, recipe in enumerate(parsed_recipes, start=1):
            print(f"{i}. {recipe['dish_name']}")

    while True:
        selection = input("\nSelect the recipe number you want to choose ('n' to skip choice): ").strip()

        if selection.lower() == 'n':
            print("Skipping logging.")
            return

        if selection.isdigit():
            selection = int(selection)
            if 1 <= selection <= len(parsed_recipes):
                break

        print("Invalid input. Try again.")

    recipe = parsed_recipes[selection-1]


    cur = db.cursor()

    
    cur.execute("""
    INSERT INTO recipes (dish_name, calories, protein, carbs, fat)
    VALUES (%s, %s, %s, %s, %s)
    """, (
        recipe["dish_name"],
        int(str(recipe["calories"]).replace("g", "")),
        int(str(recipe["protein"]).replace("g", "")),
        int(str(recipe["carbs"]).replace("g", "")),
        int(str(recipe["fat"]).replace("g", ""))
     ))

    db.commit()
    cur.close()

    #print daily nutritional value for the recipes added that day
    print_daily_total(daily_total(db))

if __name__ == "__main__":
    main()
