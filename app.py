from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import requests
import re # Import the regular expression module for text formatting
from groq import Groq # Assuming you have 'groq' library installed (pip install groq)
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# --- IMPORTANT: API KEY CONFIGURATION ---
# Load API keys from environment variables for security.
# DO NOT hardcode your actual API keys here in a production environment.

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# Provide dummy values for local testing if environment variables are not set.
# This allows the app to run without crashing, but API calls will fail until real keys are set.
if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY environment variable not set. Groq API calls will fail.")
    GROQ_API_KEY = "dummy_groq_key"
if not UNSPLASH_ACCESS_KEY:
    print("WARNING: UNSPLASH_ACCESS_KEY environment variable not set. Unsplash image fetching will fail.")
    UNSPLASH_ACCESS_KEY = "dummy_unsplash_key"
# --- END API KEY CONFIGURATION ---


def ask_groq(prompt):
    """
    Sends a prompt to the Groq API and returns the processed response.
    Bolds sections marked with **double asterisks**.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "dummy_groq_key":
        return "Sorry, Groq API key is not configured. Please set GROQ_API_KEY environment variable."

    try:
        client = Groq(api_key=GROQ_API_KEY)
        result = client.chat.completions.create(
            # Using a currently supported Groq model. 'mixtral-8x7b-32768' is decommissioned.
            model="llama3-8b-8192", # Recommended for speed and quality
            messages=[
                {"role": "system", "content": "You are a helpful AI recipe generator. Use **double asterisks** to bold important sections like 'Ingredients:', 'Steps:', and dish names."},
                {"role": "user", "content": prompt}
            ]
        )
        # Debugging: Print full response to console
        print("Full GROQ response:", result)

        if hasattr(result, 'choices') and result.choices:
            response_content = result.choices[0].message.content
            # Convert Markdown-style bolding (**) to HTML <strong> tags
            processed_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response_content)
            return processed_content
        else:
            return "Sorry, I couldn't cook anything with that input 😅"
    except Exception as e:
        print(f"Error from GROQ: {e}")
        return f"Something went wrong while talking to the recipe bot 💥: {e}"


def get_image_for_query(query, is_ingredient=False):
    """
    Fetches an image URL from Unsplash based on a query.
    Uses 'thumb' size for ingredients and 'small' for dishes.
    """
    if not UNSPLASH_ACCESS_KEY or UNSPLASH_ACCESS_KEY == "dummy_unsplash_key":
        return None # Return None if API key is not set or is a dummy

    unsplash_url = "https://api.unsplash.com/search/photos"
    # Adjust search term for better relevance
    search_term = f"{query} food recipe" if not is_ingredient else f"{query} ingredient food"
    params = {
        "query": search_term,
        "per_page": 1, # Only need one image
        "client_id": UNSPLASH_ACCESS_KEY,
        "orientation": "landscape" if not is_ingredient else "squarish" # Optimize image orientation
    }
    try:
        response = requests.get(unsplash_url, params=params)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if data and data['results']:
            # Return appropriate image size
            return data['results'][0]['urls']['small'] if not is_ingredient else data['results'][0]['urls']['thumb']
        return None # No results found
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from Unsplash for '{search_term}': {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while processing Unsplash response for '{search_term}': {e}")
        return None


# --- FLASK ROUTES ---

@app.route('/')
def index():
    """Renders the main page for ingredient input."""
    return render_template('index.html')

@app.route('/suggest', methods=['POST'])
def suggest():
    """
    Receives ingredients, asks Groq for dish suggestions,
    fetches images for each, and renders the suggestions page.
    """
    ingredients_str = request.form.get('ingredients', '')  # Get comma-separated ingredients

    prompt = f"Suggest 5 dishes I can make using: {ingredients_str}. Return only the names as a bullet list."
    response_from_groq = ask_groq(prompt)

    # 🛠️ FIX: Only keep lines that start with a bullet or dash
    raw_lines = response_from_groq.split('\n')
    dish_lines = [line for line in raw_lines if line.strip().startswith(('•', '-', '*'))]

    # 🧼 Clean up bullet symbols and <strong> tags
    dishes = [
        re.sub(r'</?strong>', '', line).strip('•-* ').strip()
        for line in dish_lines
    ]

    dishes_with_images = []
    for dish_name in dishes:
        image_url = get_image_for_query(dish_name, is_ingredient=False)  # Get image for dish
        dishes_with_images.append({'name': dish_name, 'image_url': image_url})

    return render_template('suggestions.html', dishes=dishes_with_images, ingredients=ingredients_str)


@app.route('/recipe/<dish>')
def recipe(dish):
    """
    Receives a dish name, asks Groq for the full recipe,
    fetches an image for it, and renders the recipe page.
    """
    prompt = f"Give a proper recipe for {dish} with ingredients, steps, and tips. Use **double asterisks** to bold important section headers (e.g., **Ingredients:**, **Steps:**, **Tips:**) and dish names if repeated."
    recipe_text = ask_groq(prompt)

    image_url = get_image_for_query(dish, is_ingredient=False) # Get image for recipe

    return render_template('recipe.html', dish=dish, recipe=recipe_text, image_url=image_url)


@app.route('/search_ingredients')
def search_ingredients():
    """
    Provides autocomplete suggestions for ingredients.
    Currently uses a hardcoded list; can be extended to an AI/database API.
    """
    query = request.args.get('query', '').strip()
    suggestions = []
    if query:
        # For demonstration, we'll filter from a hardcoded list.
        # In a real application, you'd call a dedicated Food Database API here
        # (e.g., Edamam, Spoonacular) for a vast, dynamic list.
        all_possible_ingredients = [
            "chicken", "rice", "tomato", "onion", "garlic", "cheese", "milk", "eggs",
            "flour", "sugar", "salt", "pepper", "butter", "oil", "potato", "carrot",
            "spinach", "broccoli", "beef", "pork", "fish", "shrimp", "pasta", "bread",
            "lemon", "lime", "ginger", "chilli", "cumin", "coriander", "paprika",
            "cream", "yogurt", "mushrooms", "bell pepper", "cucumber", "avocado", "paneer", "peas",
            "apple", "banana", "orange", "grape", "strawberry", "blueberry", "mango", "pineapple",
            "lettuce", "cabbage", "zucchini", "eggplant", "peas", "beans", "lentils", "quinoa",
            "oats", "honey", "maple syrup", "chocolate", "cocoa powder", "vanilla extract",
            "almonds", "walnuts", "cashews", "peanuts", "olives", "olive oil", "vinegar",
            "mustard", "ketchup", "mayonnaise", "soy sauce", "teriyaki sauce", "sriracha",
            "basil", "oregano", "thyme", "rosemary", "parsley", "dill", "mint", "cinnamon",
            "nutmeg", "cloves", "cardamom", "turmeric", "bay leaf", "coconut milk", "tofu", "tempeh"
        ]

        # Filter based on query (case-insensitive)
        filtered_ingredients = [
            item for item in all_possible_ingredients if query.lower() in item.lower()
        ]

        # Get images for filtered ingredients (no limit here, frontend handles display limit)
        for ingredient_name in filtered_ingredients:
            image_url = get_image_for_query(ingredient_name, is_ingredient=True)
            suggestions.append({
                'name': ingredient_name,
                # Fallback to a local placeholder if Unsplash doesn't return an image
                'image': image_url if image_url else '/static/placeholder_ingredient.png'
            })
    return jsonify(suggestions)


if __name__ == "__main__":
    # In a production environment, use a production-ready WSGI server like Gunicorn or uWSGI.
    # For local development:
    app.run(debug=True)
