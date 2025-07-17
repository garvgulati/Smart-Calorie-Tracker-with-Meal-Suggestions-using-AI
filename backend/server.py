from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date
import google.generativeai as genai
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configure Gemini AI
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    age: int
    gender: str
    activity_level: str
    goal: str  # fat_loss, maintenance, muscle_gain
    daily_calorie_target: int
    macro_split: Dict[str, int]  # protein, carbs, fat percentages
    dietary_preferences: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str
    age: int
    gender: str
    activity_level: str
    goal: str
    daily_calorie_target: int
    macro_split: Dict[str, int]
    dietary_preferences: List[str] = []

class FoodItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FoodItemCreate(BaseModel):
    name: str
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float

class MealEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    food_name: str
    amount_grams: float
    meal_type: str  # breakfast, lunch, dinner, snack
    calories: float
    protein: float
    carbs: float
    fat: float
    date: str  # ISO format string
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MealEntryCreate(BaseModel):
    user_id: str
    food_name: str
    amount_grams: float
    meal_type: str
    calories: float
    protein: float
    carbs: float
    fat: float

class DailySummary(BaseModel):
    date: str  # ISO format string
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    calorie_target: int
    protein_target: float
    carbs_target: float
    fat_target: float
    meals: List[MealEntry]

class AIFoodSuggestion(BaseModel):
    meal_name: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    serving_size: str
    ingredients: List[str]
    recipe: str
    cooking_time: str
    reason: str

class AIMealSuggestionRequest(BaseModel):
    user_id: str
    current_date: str  # ISO format string
    remaining_calories: float
    remaining_protein: float
    remaining_carbs: float
    remaining_fat: float
    meal_type: str
    dietary_preferences: List[str] = []

# User endpoints
@api_router.post("/users", response_model=User)
async def create_user(user: UserCreate):
    user_dict = user.dict()
    user_obj = User(**user_dict)
    await db.users.insert_one(user_obj.dict())
    return user_obj

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

@api_router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find().to_list(1000)
    return [User(**user) for user in users]

# Food database endpoints
@api_router.post("/foods", response_model=FoodItem)
async def create_food_item(food: FoodItemCreate):
    food_dict = food.dict()
    food_obj = FoodItem(**food_dict)
    await db.foods.insert_one(food_obj.dict())
    return food_obj

@api_router.get("/foods/search/{query}")
async def search_foods(query: str):
    foods = await db.foods.find({"name": {"$regex": query, "$options": "i"}}).to_list(20)
    return [FoodItem(**food) for food in foods]

@api_router.get("/foods", response_model=List[FoodItem])
async def get_foods():
    foods = await db.foods.find().to_list(100)
    return [FoodItem(**food) for food in foods]

# Meal tracking endpoints
@api_router.post("/meals", response_model=MealEntry)
async def create_meal_entry(meal: MealEntryCreate):
    meal_dict = meal.dict()
    meal_dict['date'] = date.today().isoformat()  # Convert to ISO format string
    meal_obj = MealEntry(**meal_dict)
    await db.meals.insert_one(meal_obj.dict())
    return meal_obj

@api_router.get("/meals/{user_id}/{date_str}")
async def get_meals_for_date(user_id: str, date_str: str):
    query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    meals = await db.meals.find({"user_id": user_id, "date": query_date.isoformat()}).to_list(1000)
    return [MealEntry(**meal) for meal in meals]

@api_router.delete("/meals/{meal_id}")
async def delete_meal(meal_id: str):
    result = await db.meals.delete_one({"id": meal_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meal not found")
    return {"message": "Meal deleted successfully"}

# Daily summary endpoint
@api_router.get("/daily-summary/{user_id}/{date_str}", response_model=DailySummary)
async def get_daily_summary(user_id: str, date_str: str):
    query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Get user info
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get meals for the day
    meals = await db.meals.find({"user_id": user_id, "date": query_date.isoformat()}).to_list(1000)
    meal_entries = [MealEntry(**meal) for meal in meals]
    
    # Calculate totals
    total_calories = sum(meal.calories for meal in meal_entries)
    total_protein = sum(meal.protein for meal in meal_entries)
    total_carbs = sum(meal.carbs for meal in meal_entries)
    total_fat = sum(meal.fat for meal in meal_entries)
    
    # Calculate targets based on user's macro split
    calorie_target = user['daily_calorie_target']
    protein_target = (calorie_target * user['macro_split']['protein'] / 100) / 4  # 4 cal/g
    carbs_target = (calorie_target * user['macro_split']['carbs'] / 100) / 4  # 4 cal/g
    fat_target = (calorie_target * user['macro_split']['fat'] / 100) / 9  # 9 cal/g
    
    return DailySummary(
        date=query_date.isoformat(),
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat,
        calorie_target=calorie_target,
        protein_target=protein_target,
        carbs_target=carbs_target,
        fat_target=fat_target,
        meals=meal_entries
    )

# AI meal suggestions endpoint
@api_router.post("/ai-meal-suggestions")
async def get_ai_meal_suggestions(request: AIMealSuggestionRequest):
    try:
        # Create prompt for Gemini
        dietary_prefs = ", ".join(request.dietary_preferences) if request.dietary_preferences else "no specific preferences"
        
        prompt = f"""
        I need complete meal suggestions for {request.meal_type} with the following nutritional requirements:
        - Remaining calories: {request.remaining_calories}
        - Remaining protein: {request.remaining_protein}g
        - Remaining carbs: {request.remaining_carbs}g
        - Remaining fat: {request.remaining_fat}g
        - Dietary preferences: {dietary_prefs}
        
        Please suggest 3 complete, ready-to-eat meals (not individual ingredients) that would help reach these macro targets. 
        Include full recipes with all ingredients, sauces, and cooking steps.
        
        Examples of complete meals: "Chicken Burrito Bowl", "Veggie Omelette", "Tandoori Chicken with Rice", "Paneer Tikka Wrap", "Omu Rice", "Protein Smoothie Bowl"
        
        Return ONLY a JSON array with this exact format:
        [
            {{
                "meal_name": "Complete meal name (e.g., Chicken Burrito Bowl)",
                "total_calories": 450,
                "total_protein": 35,
                "total_carbs": 40,
                "total_fat": 15,
                "serving_size": "1 bowl (approximately 350g)",
                "ingredients": [
                    "150g grilled chicken breast",
                    "80g brown rice",
                    "50g black beans",
                    "30g cheddar cheese",
                    "40g avocado",
                    "20g salsa",
                    "10g sour cream",
                    "Mixed greens"
                ],
                "recipe": "1. Cook brown rice according to package instructions. 2. Season chicken breast with cumin, paprika, salt and pepper. Grill for 6-8 minutes each side. 3. Warm black beans in a pan. 4. In a bowl, layer rice, beans, sliced chicken, cheese, avocado, salsa, and sour cream. 5. Garnish with mixed greens.",
                "cooking_time": "20 minutes",
                "reason": "High protein meal with balanced macros, provides sustained energy and fits remaining calorie target"
            }}
        ]
        
        Make sure each meal is:
        - Complete and ready to eat
        - Includes all ingredients with approximate amounts
        - Has detailed cooking instructions
        - Matches the dietary preferences
        - Has accurate nutritional calculations for the entire meal
        - Is realistic and commonly prepared
        """
        
        response = model.generate_content(prompt)
        
        # Parse the response
        try:
            # Extract JSON from response
            response_text = response.text.strip()
            # Remove any markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '')
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '')
            
            suggestions = json.loads(response_text)
            return {"suggestions": suggestions}
            
        except json.JSONDecodeError:
            # Fallback suggestions if JSON parsing fails
            return {
                "suggestions": [
                    {
                        "food_name": "Grilled Chicken Breast",
                        "amount_grams": 100,
                        "calories": 165,
                        "protein": 31,
                        "carbs": 0,
                        "fat": 3.6,
                        "reason": "High protein, low fat, fits most dietary preferences"
                    },
                    {
                        "food_name": "Brown Rice",
                        "amount_grams": 100,
                        "calories": 111,
                        "protein": 2.6,
                        "carbs": 23,
                        "fat": 0.9,
                        "reason": "Good source of complex carbs"
                    },
                    {
                        "food_name": "Avocado",
                        "amount_grams": 50,
                        "calories": 80,
                        "protein": 1,
                        "carbs": 4,
                        "fat": 7,
                        "reason": "Healthy fats and fiber"
                    }
                ]
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# AI food lookup endpoint
@api_router.post("/ai-food-lookup")
async def ai_food_lookup(request: Dict[str, Any]):
    try:
        food_name = request.get("food_name", "")
        
        prompt = f"""
        Please provide nutritional information for "{food_name}" per 100g.
        Return ONLY a JSON object with this exact format:
        {{
            "name": "exact food name",
            "calories_per_100g": 250,
            "protein_per_100g": 20,
            "carbs_per_100g": 30,
            "fat_per_100g": 8
        }}
        
        If the food is not recognizable, return an error message.
        """
        
        response = model.generate_content(prompt)
        
        try:
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '')
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '')
            
            nutrition_data = json.loads(response_text)
            return nutrition_data
            
        except json.JSONDecodeError:
            return {
                "error": "Could not parse nutritional information for this food"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# Populate initial food database
@api_router.post("/populate-food-database")
async def populate_food_database():
    """Populate the database with common foods"""
    common_foods = [
        {"name": "Chicken Breast", "calories_per_100g": 165, "protein_per_100g": 31, "carbs_per_100g": 0, "fat_per_100g": 3.6},
        {"name": "Brown Rice", "calories_per_100g": 111, "protein_per_100g": 2.6, "carbs_per_100g": 23, "fat_per_100g": 0.9},
        {"name": "Avocado", "calories_per_100g": 160, "protein_per_100g": 2, "carbs_per_100g": 9, "fat_per_100g": 15},
        {"name": "Banana", "calories_per_100g": 89, "protein_per_100g": 1.1, "carbs_per_100g": 23, "fat_per_100g": 0.3},
        {"name": "Salmon", "calories_per_100g": 208, "protein_per_100g": 25, "carbs_per_100g": 0, "fat_per_100g": 12},
        {"name": "Greek Yogurt", "calories_per_100g": 59, "protein_per_100g": 10, "carbs_per_100g": 3.6, "fat_per_100g": 0.4},
        {"name": "Oats", "calories_per_100g": 389, "protein_per_100g": 16.9, "carbs_per_100g": 66, "fat_per_100g": 6.9},
        {"name": "Eggs", "calories_per_100g": 155, "protein_per_100g": 13, "carbs_per_100g": 1.1, "fat_per_100g": 11},
        {"name": "Broccoli", "calories_per_100g": 34, "protein_per_100g": 2.8, "carbs_per_100g": 7, "fat_per_100g": 0.4},
        {"name": "Sweet Potato", "calories_per_100g": 86, "protein_per_100g": 1.6, "carbs_per_100g": 20, "fat_per_100g": 0.1}
    ]
    
    for food_data in common_foods:
        food_obj = FoodItem(**food_data)
        await db.foods.insert_one(food_obj.dict())
    
    return {"message": f"Added {len(common_foods)} foods to database"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()