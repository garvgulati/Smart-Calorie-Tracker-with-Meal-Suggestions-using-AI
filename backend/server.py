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
    meal_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "vegetarian": False,
        "vegan": False,
        "gluten_free": False,
        "dairy_free": False,
        "high_protein": False,
        "low_carb": False,
        "keto": False,
        "paleo": False,
        "indian": False,
        "mediterranean": False,
        "asian": False,
        "mexican": False,
        "italian": False,
        "american": False
    })
    recent_suggestions: List[str] = []  # Track recent meal suggestions
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
    meal_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "vegetarian": False,
        "vegan": False,
        "gluten_free": False,
        "dairy_free": False,
        "high_protein": False,
        "low_carb": False,
        "keto": False,
        "paleo": False,
        "indian": False,
        "mediterranean": False,
        "asian": False,
        "mexican": False,
        "italian": False,
        "american": False
    })

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
    micronutrients: Dict[str, str] = Field(default_factory=lambda: {
        "vitamin_c": "0mg",
        "iron": "0mg",
        "calcium": "0mg",
        "fiber": "0g",
        "sodium": "0mg",
        "potassium": "0mg"
    })
    cuisine_type: str = "General"

class AIMealSuggestionRequest(BaseModel):
    user_id: str
    current_date: str  # ISO format string
    remaining_calories: float
    remaining_protein: float
    remaining_carbs: float
    remaining_fat: float
    meal_type: str
    dietary_preferences: List[str] = []
    meal_preferences: Dict[str, bool] = Field(default_factory=dict)
    exclude_recent: List[str] = []  # Recently suggested meals to avoid

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
        # Get user preferences
        user = await db.users.find_one({"id": request.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build dietary preferences string
        active_preferences = []
        meal_prefs = request.meal_preferences or user.get('meal_preferences', {})
        
        for pref, enabled in meal_prefs.items():
            if enabled:
                active_preferences.append(pref.replace('_', ' '))
        
        if request.dietary_preferences:
            active_preferences.extend(request.dietary_preferences)
        
        dietary_prefs = ", ".join(active_preferences) if active_preferences else "no specific preferences"
        
        # Build excluded meals string
        excluded_meals = ", ".join(request.exclude_recent) if request.exclude_recent else "none"
        
        # Meal timing context
        meal_timing_context = {
            "breakfast": "light, energizing meals suitable for morning consumption",
            "lunch": "substantial, balanced meals for midday energy",
            "dinner": "satisfying, complete meals for evening consumption",
            "snack": "quick, portable options for between meals"
        }
        
        timing_context = meal_timing_context.get(request.meal_type, "balanced meals")
        
        # Create enhanced prompt for Gemini
        prompt = f"""
        I need complete {request.meal_type} meal suggestions with the following requirements:
        
        NUTRITIONAL TARGETS:
        - Remaining calories: {request.remaining_calories}
        - Remaining protein: {request.remaining_protein}g
        - Remaining carbs: {request.remaining_carbs}g
        - Remaining fat: {request.remaining_fat}g
        
        MEAL CONTEXT:
        - Meal type: {request.meal_type} ({timing_context})
        - Dietary preferences: {dietary_prefs}
        - Recently suggested meals to AVOID: {excluded_meals}
        
        Please suggest 3 complete, diverse meals that:
        1. Are appropriate for {request.meal_type} timing
        2. Match the dietary preferences
        3. Are completely different from recently suggested meals
        4. Include micronutrient information
        5. Have varied cuisine types
        
        Return ONLY a JSON array with this exact format:
        [
            {{
                "meal_name": "Complete meal name (e.g., Mediterranean Quinoa Bowl)",
                "total_calories": 450,
                "total_protein": 35,
                "total_carbs": 40,
                "total_fat": 15,
                "serving_size": "1 bowl (approximately 350g)",
                "ingredients": [
                    "100g quinoa",
                    "120g grilled chicken breast",
                    "50g cherry tomatoes",
                    "40g cucumber",
                    "30g feta cheese",
                    "20g olives",
                    "15ml olive oil",
                    "10ml lemon juice",
                    "Fresh herbs"
                ],
                "recipe": "1. Cook quinoa according to package instructions. 2. Season and grill chicken breast. 3. Chop vegetables. 4. Combine all ingredients in bowl. 5. Drizzle with olive oil and lemon juice. 6. Garnish with fresh herbs.",
                "cooking_time": "25 minutes",
                "reason": "High protein Mediterranean meal with complete amino acids and healthy fats",
                "micronutrients": {{
                    "vitamin_c": "45mg",
                    "iron": "3.2mg",
                    "calcium": "150mg",
                    "fiber": "8g",
                    "sodium": "420mg",
                    "potassium": "680mg"
                }},
                "cuisine_type": "Mediterranean"
            }}
        ]
        
        IMPORTANT:
        - Make meals appropriate for {request.meal_type}
        - Ensure variety in cuisine types (Mediterranean, Asian, Indian, Mexican, etc.)
        - Include accurate micronutrient estimates
        - Avoid repeating: {excluded_meals}
        - Match dietary preferences: {dietary_prefs}
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
            
            # Update user's recent suggestions
            meal_names = [s.get('meal_name', '') for s in suggestions]
            recent_suggestions = user.get('recent_suggestions', [])
            recent_suggestions.extend(meal_names)
            # Keep only last 15 suggestions
            recent_suggestions = recent_suggestions[-15:]
            
            await db.users.update_one(
                {"id": request.user_id},
                {"$set": {"recent_suggestions": recent_suggestions}}
            )
            
            return {"suggestions": suggestions}
            
        except json.JSONDecodeError:
            # Enhanced fallback suggestions with micronutrients
            fallback_suggestions = {
                "breakfast": [
                    {
                        "meal_name": "Protein Pancakes with Berries",
                        "total_calories": 380,
                        "total_protein": 25,
                        "total_carbs": 45,
                        "total_fat": 12,
                        "serving_size": "2 pancakes with toppings",
                        "ingredients": [
                            "40g protein powder",
                            "1 banana",
                            "2 eggs",
                            "100g mixed berries",
                            "15ml maple syrup",
                            "5g coconut oil"
                        ],
                        "recipe": "1. Mash banana and mix with eggs and protein powder. 2. Cook pancakes in coconut oil. 3. Top with berries and maple syrup.",
                        "cooking_time": "15 minutes",
                        "reason": "High protein breakfast with antioxidants and sustained energy",
                        "micronutrients": {
                            "vitamin_c": "60mg",
                            "iron": "2.5mg",
                            "calcium": "120mg",
                            "fiber": "6g",
                            "sodium": "180mg",
                            "potassium": "450mg"
                        },
                        "cuisine_type": "American"
                    }
                ],
                "lunch": [
                    {
                        "meal_name": "Mediterranean Quinoa Bowl",
                        "total_calories": 520,
                        "total_protein": 32,
                        "total_carbs": 55,
                        "total_fat": 18,
                        "serving_size": "1 bowl (400g)",
                        "ingredients": [
                            "100g quinoa",
                            "120g grilled chicken",
                            "50g cherry tomatoes",
                            "40g cucumber",
                            "30g feta cheese",
                            "20g olives",
                            "15ml olive oil"
                        ],
                        "recipe": "1. Cook quinoa. 2. Grill chicken with herbs. 3. Chop vegetables. 4. Combine in bowl with olive oil dressing.",
                        "cooking_time": "25 minutes",
                        "reason": "Complete protein with healthy fats and complex carbs",
                        "micronutrients": {
                            "vitamin_c": "45mg",
                            "iron": "3.2mg",
                            "calcium": "150mg",
                            "fiber": "8g",
                            "sodium": "420mg",
                            "potassium": "680mg"
                        },
                        "cuisine_type": "Mediterranean"
                    }
                ],
                "dinner": [
                    {
                        "meal_name": "Tandoori Chicken with Basmati Rice",
                        "total_calories": 580,
                        "total_protein": 42,
                        "total_carbs": 60,
                        "total_fat": 16,
                        "serving_size": "1 plate (450g)",
                        "ingredients": [
                            "150g chicken breast",
                            "100g basmati rice",
                            "50g Greek yogurt",
                            "Tandoori spices",
                            "30g onions",
                            "20g cilantro",
                            "10ml lemon juice"
                        ],
                        "recipe": "1. Marinate chicken in yogurt and spices. 2. Cook basmati rice. 3. Grill chicken until cooked through. 4. Serve with rice and garnish.",
                        "cooking_time": "35 minutes",
                        "reason": "High protein Indian meal with aromatic spices and complete nutrition",
                        "micronutrients": {
                            "vitamin_c": "25mg",
                            "iron": "2.8mg",
                            "calcium": "180mg",
                            "fiber": "3g",
                            "sodium": "480mg",
                            "potassium": "720mg"
                        },
                        "cuisine_type": "Indian"
                    }
                ],
                "snack": [
                    {
                        "meal_name": "Greek Yogurt Parfait",
                        "total_calories": 280,
                        "total_protein": 18,
                        "total_carbs": 32,
                        "total_fat": 8,
                        "serving_size": "1 cup (250g)",
                        "ingredients": [
                            "150g Greek yogurt",
                            "30g granola",
                            "80g mixed berries",
                            "10g honey",
                            "5g almonds"
                        ],
                        "recipe": "1. Layer yogurt, berries, and granola. 2. Drizzle with honey. 3. Top with almonds.",
                        "cooking_time": "5 minutes",
                        "reason": "Protein-rich snack with probiotics and antioxidants",
                        "micronutrients": {
                            "vitamin_c": "50mg",
                            "iron": "1.2mg",
                            "calcium": "200mg",
                            "fiber": "4g",
                            "sodium": "80mg",
                            "potassium": "320mg"
                        },
                        "cuisine_type": "Mediterranean"
                    }
                ]
            }
            
            meal_suggestions = fallback_suggestions.get(request.meal_type, fallback_suggestions["lunch"])
            return {"suggestions": meal_suggestions}
            
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