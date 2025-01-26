from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import spacy

# Load SpaCy model and BERT model
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["userDB"] 


# Predefined list of skills
SKILL_KEYWORDS = [
    "Python", "Machine Learning", "Data Analysis", "Frontend Development", 
    "JavaScript", "React", "Backend Development", "Node.js", "MongoDB", 
    "UI/UX Design", "Figma", "Adobe XD", "Deep Learning", "TensorFlow", 
    "CSS", "Express", "Prototyping", "Java", "C++", "HTML", "SQL", "AI", 
    "Django", "Flask"
]

# FastAPI app initialization
app = FastAPI()

class Query(BaseModel):
    user_input: str


# Helper function to extract skills from input
def extract_skills(input_text):
    doc = nlp(input_text)
    extracted_skills = []

    for skill in SKILL_KEYWORDS:
        if skill.lower() in input_text.lower():
            extracted_skills.append(skill)
    
    for token in doc:
        if token.text in SKILL_KEYWORDS and token.text not in extracted_skills:
            extracted_skills.append(token.text)
    return extracted_skills

# Helper function to search for users
def search_users_by_skills(input_skills):
    users = db.users.find()  # Retrieve all users from the database
    results = []
    for user in users:
        user_skills = user.get("skills", [])
        if user_skills:
            matched_skills = list(set(input_skills) & set(user_skills))  # Find the intersection of input skills and user skills
            if matched_skills:
                results.append({
                    "Username": user.get("username"),
                    "Matched Skills": ", ".join(matched_skills),
                    "Match Count": len(matched_skills)
                })
    
    # Check if results are found
    if not results:
        return {"status": "failure", "data": [], "message": "No users found matching the given skills."}
    
    # Return sorted results based on match count (in descending order)
    return sorted(results, key=lambda x: x["Match Count"], reverse=True)

# Helper function to search for teams
def search_teams_by_skills(input_skills):
    teams = db.teams.find()
    results = []
    for team in teams:
        team_skills = team.get("skillsRequired", [])
        if team_skills:
            matched_skills = list(set(input_skills) & set(team_skills))
            if matched_skills:
                results.append({
                    "Team Name": team.get("teamName"),
                    "Matched Skills": ", ".join(matched_skills),
                    "Match Count": len(matched_skills)
                })
    return sorted(results, key=lambda x: x["Match Count"], reverse=True)

# Helper function to show all users
def show_all_users():
    users = db.users.find()
    return [user.get("username") for user in users]

# Helper function to show all teams
def show_all_teams():
    teams = db.teams.find()
    return [{
        "Team Name": team.get("teamName"),
        "Required Skills": ", ".join(team.get("skillsRequired", [])),
        "Slots Available": team.get("slotsAvailable")
    } for team in teams]
# API endpoints

@app.post("/search")
async def search(query: Query):
    user_input = query.user_input
    response = {}

    if "show all users" in user_input.lower():
        users = show_all_users()
        if users:
            response = {"status": "success", "data": users, "message": "All users retrieved successfully."}
        else:
            response = {"status": "failure", "data": [], "message": "No users found."}
    elif "show all teams" in user_input.lower():
        teams = show_all_teams()
        if teams:
            response = {"status": "success", "data": teams, "message": "All teams retrieved successfully."}
        else:
            response = {"status": "failure", "data": [], "message": "No teams found."}
    else:
        extracted_skills = extract_skills(user_input)

        if extracted_skills:
            if "user" in user_input.lower():
                user_results = search_users_by_skills(extracted_skills)
                if user_results:
                    response = {"status": "success", "data": user_results, "message": f"Users matching the skills: {', '.join(extracted_skills)}"}
                else:
                    response = {"status": "failure", "data": [], "message": "No users found matching the given skills."}
            elif "team" in user_input.lower():
                team_results = search_teams_by_skills(extracted_skills)
                if team_results:
                    response = {"status": "success", "data": team_results, "message": f"Teams matching the skills: {', '.join(extracted_skills)}"}
                else:
                    response = {"status": "failure", "data": [], "message": "No teams found matching the given skills."}
            else:
                response = {"status": "error", "data": [], "message": "Please specify whether you are looking for 'users' or 'teams'."}
        else:
            response = {"status": "error", "data": [], "message": "No relevant skills found in your input."}

    return response

# For running the API with Uvicorn
# uvicorn filename:app --reload
 