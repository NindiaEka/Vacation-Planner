# user_preferences.py
import json

def get_preferences():
    with open('data/user_preferences.json', 'r') as f:
        return json.load(f)
