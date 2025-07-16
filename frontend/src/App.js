import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [user, setUser] = useState(null);
  const [dailySummary, setDailySummary] = useState(null);
  const [mealEntry, setMealEntry] = useState({
    food_name: '',
    amount_grams: 100,
    meal_type: 'breakfast',
    calories: 0,
    protein: 0,
    carbs: 0,
    fat: 0
  });
  const [aiSuggestions, setAiSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [setupData, setSetupData] = useState({
    name: '',
    age: 25,
    gender: 'male',
    activity_level: 'moderate',
    goal: 'maintenance',
    daily_calorie_target: 2000,
    macro_split: { protein: 30, carbs: 40, fat: 30 },
    dietary_preferences: []
  });

  const today = new Date().toISOString().split('T')[0];

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      // Check if user exists (for demo, we'll use a default user)
      const response = await axios.get(`${API}/users`);
      if (response.data.length > 0) {
        setUser(response.data[0]);
        loadDailySummary(response.data[0].id);
      }
    } catch (error) {
      console.error('Error initializing app:', error);
    }
  };

  const loadDailySummary = async (userId) => {
    try {
      const response = await axios.get(`${API}/daily-summary/${userId}/${today}`);
      setDailySummary(response.data);
    } catch (error) {
      console.error('Error loading daily summary:', error);
    }
  };

  const createUser = async () => {
    try {
      const response = await axios.post(`${API}/users`, setupData);
      setUser(response.data);
      setCurrentView('dashboard');
      
      // Populate food database
      await axios.post(`${API}/populate-food-database`);
      
      loadDailySummary(response.data.id);
    } catch (error) {
      console.error('Error creating user:', error);
    }
  };

  const addMealEntry = async () => {
    if (!user) return;
    
    try {
      const entryData = {
        ...mealEntry,
        user_id: user.id
      };
      
      await axios.post(`${API}/meals`, entryData);
      
      // Reset form
      setMealEntry({
        food_name: '',
        amount_grams: 100,
        meal_type: 'breakfast',
        calories: 0,
        protein: 0,
        carbs: 0,
        fat: 0
      });
      
      // Reload daily summary
      loadDailySummary(user.id);
    } catch (error) {
      console.error('Error adding meal:', error);
    }
  };

  const lookupFood = async (foodName) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/ai-food-lookup`, { food_name: foodName });
      
      if (response.data.error) {
        alert(response.data.error);
        return;
      }
      
      setMealEntry(prev => ({
        ...prev,
        food_name: response.data.name,
        calories: (response.data.calories_per_100g * prev.amount_grams) / 100,
        protein: (response.data.protein_per_100g * prev.amount_grams) / 100,
        carbs: (response.data.carbs_per_100g * prev.amount_grams) / 100,
        fat: (response.data.fat_per_100g * prev.amount_grams) / 100
      }));
    } catch (error) {
      console.error('Error looking up food:', error);
      alert('Error looking up food information');
    } finally {
      setLoading(false);
    }
  };

  const getAISuggestions = async (mealType) => {
    if (!user || !dailySummary) return;
    
    try {
      setLoading(true);
      
      const remainingCalories = dailySummary.calorie_target - dailySummary.total_calories;
      const remainingProtein = dailySummary.protein_target - dailySummary.total_protein;
      const remainingCarbs = dailySummary.carbs_target - dailySummary.total_carbs;
      const remainingFat = dailySummary.fat_target - dailySummary.total_fat;
      
      const response = await axios.post(`${API}/ai-meal-suggestions`, {
        user_id: user.id,
        current_date: today,
        remaining_calories: remainingCalories,
        remaining_protein: remainingProtein,
        remaining_carbs: remainingCarbs,
        remaining_fat: remainingFat,
        meal_type: mealType,
        dietary_preferences: user.dietary_preferences
      });
      
      setAiSuggestions(response.data.suggestions);
    } catch (error) {
      console.error('Error getting AI suggestions:', error);
      alert('Error getting meal suggestions');
    } finally {
      setLoading(false);
    }
  };

  const addSuggestionToMeal = (suggestion) => {
    setMealEntry({
      food_name: suggestion.food_name,
      amount_grams: suggestion.amount_grams,
      meal_type: mealEntry.meal_type,
      calories: suggestion.calories,
      protein: suggestion.protein,
      carbs: suggestion.carbs,
      fat: suggestion.fat
    });
    setAiSuggestions([]);
  };

  const calculateMacroPercentages = () => {
    if (!dailySummary) return { protein: 0, carbs: 0, fat: 0 };
    
    const totalCals = dailySummary.total_calories;
    if (totalCals === 0) return { protein: 0, carbs: 0, fat: 0 };
    
    return {
      protein: Math.round((dailySummary.total_protein * 4 / totalCals) * 100),
      carbs: Math.round((dailySummary.total_carbs * 4 / totalCals) * 100),
      fat: Math.round((dailySummary.total_fat * 9 / totalCals) * 100)
    };
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-900 via-emerald-800 to-emerald-900 p-4">
        <div className="max-w-2xl mx-auto pt-12">
          <div className="bg-emerald-800/30 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-emerald-700/50">
            <h1 className="text-4xl font-bold text-amber-400 mb-2 text-center">🍎 Smart Macro Tracker</h1>
            <p className="text-emerald-100 text-center mb-8">AI-powered nutrition tracking with personalized meal suggestions</p>
            
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-emerald-200 mb-2">Name</label>
                  <input
                    type="text"
                    value={setupData.name}
                    onChange={(e) => setSetupData({...setupData, name: e.target.value})}
                    className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white placeholder-emerald-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
                    placeholder="Enter your name"
                  />
                </div>
                
                <div>
                  <label className="block text-emerald-200 mb-2">Age</label>
                  <input
                    type="number"
                    value={setupData.age}
                    onChange={(e) => setSetupData({...setupData, age: parseInt(e.target.value)})}
                    className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-emerald-200 mb-2">Gender</label>
                  <select
                    value={setupData.gender}
                    onChange={(e) => setSetupData({...setupData, gender: e.target.value})}
                    className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-emerald-200 mb-2">Activity Level</label>
                  <select
                    value={setupData.activity_level}
                    onChange={(e) => setSetupData({...setupData, activity_level: e.target.value})}
                    className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                  >
                    <option value="sedentary">Sedentary</option>
                    <option value="light">Light</option>
                    <option value="moderate">Moderate</option>
                    <option value="active">Active</option>
                    <option value="very_active">Very Active</option>
                  </select>
                </div>
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Goal</label>
                <select
                  value={setupData.goal}
                  onChange={(e) => setSetupData({...setupData, goal: e.target.value})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                  <option value="fat_loss">Fat Loss</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="muscle_gain">Muscle Gain</option>
                </select>
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Daily Calorie Target</label>
                <input
                  type="number"
                  value={setupData.daily_calorie_target}
                  onChange={(e) => setSetupData({...setupData, daily_calorie_target: parseInt(e.target.value)})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-4">Macro Split (%)</label>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-emerald-300 mb-2">Protein</label>
                    <input
                      type="number"
                      value={setupData.macro_split.protein}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        macro_split: {...setupData.macro_split, protein: parseInt(e.target.value)}
                      })}
                      className="w-full px-3 py-2 bg-emerald-900/50 border border-emerald-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                    />
                  </div>
                  <div>
                    <label className="block text-emerald-300 mb-2">Carbs</label>
                    <input
                      type="number"
                      value={setupData.macro_split.carbs}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        macro_split: {...setupData.macro_split, carbs: parseInt(e.target.value)}
                      })}
                      className="w-full px-3 py-2 bg-emerald-900/50 border border-emerald-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                    />
                  </div>
                  <div>
                    <label className="block text-emerald-300 mb-2">Fat</label>
                    <input
                      type="number"
                      value={setupData.macro_split.fat}
                      onChange={(e) => setSetupData({
                        ...setupData,
                        macro_split: {...setupData.macro_split, fat: parseInt(e.target.value)}
                      })}
                      className="w-full px-3 py-2 bg-emerald-900/50 border border-emerald-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                    />
                  </div>
                </div>
              </div>
              
              <button
                onClick={createUser}
                className="w-full bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-600 hover:to-amber-500 text-emerald-900 font-bold py-4 px-6 rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg"
              >
                Start Tracking 🚀
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const currentMacros = calculateMacroPercentages();

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-900 via-emerald-800 to-emerald-900 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-emerald-800/30 backdrop-blur-md rounded-2xl p-6 mb-6 shadow-2xl border border-emerald-700/50">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-amber-400 mb-2">🍎 Smart Macro Tracker</h1>
              <p className="text-emerald-200">Welcome back, {user.name}!</p>
            </div>
            <div className="flex gap-4 mt-4 md:mt-0">
              <button
                onClick={() => setCurrentView('dashboard')}
                className={`px-6 py-3 rounded-lg font-semibold transition-all duration-300 ${
                  currentView === 'dashboard' 
                    ? 'bg-amber-400 text-emerald-900' 
                    : 'bg-emerald-700 text-emerald-200 hover:bg-emerald-600'
                }`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setCurrentView('add-meal')}
                className={`px-6 py-3 rounded-lg font-semibold transition-all duration-300 ${
                  currentView === 'add-meal' 
                    ? 'bg-amber-400 text-emerald-900' 
                    : 'bg-emerald-700 text-emerald-200 hover:bg-emerald-600'
                }`}
              >
                Add Meal
              </button>
            </div>
          </div>
        </div>

        {/* Dashboard View */}
        {currentView === 'dashboard' && dailySummary && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Daily Progress */}
            <div className="bg-emerald-800/30 backdrop-blur-md rounded-2xl p-6 shadow-2xl border border-emerald-700/50">
              <h2 className="text-2xl font-bold text-amber-400 mb-4">📊 Today's Progress</h2>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-emerald-200">Calories</span>
                    <span className="text-white">{Math.round(dailySummary.total_calories)} / {dailySummary.calorie_target}</span>
                  </div>
                  <div className="w-full bg-emerald-900/50 rounded-full h-3">
                    <div 
                      className="bg-gradient-to-r from-amber-500 to-amber-400 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min((dailySummary.total_calories / dailySummary.calorie_target) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-emerald-200">Protein</span>
                    <span className="text-white">{Math.round(dailySummary.total_protein)}g / {Math.round(dailySummary.protein_target)}g</span>
                  </div>
                  <div className="w-full bg-emerald-900/50 rounded-full h-3">
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-blue-400 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min((dailySummary.total_protein / dailySummary.protein_target) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-emerald-200">Carbs</span>
                    <span className="text-white">{Math.round(dailySummary.total_carbs)}g / {Math.round(dailySummary.carbs_target)}g</span>
                  </div>
                  <div className="w-full bg-emerald-900/50 rounded-full h-3">
                    <div 
                      className="bg-gradient-to-r from-green-500 to-green-400 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min((dailySummary.total_carbs / dailySummary.carbs_target) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-emerald-200">Fat</span>
                    <span className="text-white">{Math.round(dailySummary.total_fat)}g / {Math.round(dailySummary.fat_target)}g</span>
                  </div>
                  <div className="w-full bg-emerald-900/50 rounded-full h-3">
                    <div 
                      className="bg-gradient-to-r from-purple-500 to-purple-400 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min((dailySummary.total_fat / dailySummary.fat_target) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              <div className="mt-6 p-4 bg-emerald-900/50 rounded-lg">
                <h3 className="text-lg font-semibold text-amber-400 mb-2">Current Macro Split</h3>
                <div className="flex justify-between text-sm">
                  <span className="text-blue-300">Protein: {currentMacros.protein}%</span>
                  <span className="text-green-300">Carbs: {currentMacros.carbs}%</span>
                  <span className="text-purple-300">Fat: {currentMacros.fat}%</span>
                </div>
              </div>
            </div>

            {/* AI Suggestions */}
            <div className="bg-emerald-800/30 backdrop-blur-md rounded-2xl p-6 shadow-2xl border border-emerald-700/50">
              <h2 className="text-2xl font-bold text-amber-400 mb-4">🤖 AI Meal Suggestions</h2>
              
              <div className="space-y-3 mb-4">
                <button
                  onClick={() => getAISuggestions('breakfast')}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-orange-500 to-orange-400 hover:from-orange-600 hover:to-orange-500 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-300 disabled:opacity-50"
                >
                  🌅 Breakfast Ideas
                </button>
                <button
                  onClick={() => getAISuggestions('lunch')}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-yellow-500 to-yellow-400 hover:from-yellow-600 hover:to-yellow-500 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-300 disabled:opacity-50"
                >
                  🌞 Lunch Ideas
                </button>
                <button
                  onClick={() => getAISuggestions('dinner')}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-indigo-500 to-indigo-400 hover:from-indigo-600 hover:to-indigo-500 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-300 disabled:opacity-50"
                >
                  🌙 Dinner Ideas
                </button>
                <button
                  onClick={() => getAISuggestions('snack')}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-pink-500 to-pink-400 hover:from-pink-600 hover:to-pink-500 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-300 disabled:opacity-50"
                >
                  🍿 Snack Ideas
                </button>
              </div>

              {loading && (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-400 mx-auto"></div>
                  <p className="text-emerald-200 mt-2">Getting AI suggestions...</p>
                </div>
              )}

              {aiSuggestions.length > 0 && (
                <div className="space-y-3">
                  {aiSuggestions.map((suggestion, index) => (
                    <div key={index} className="bg-emerald-900/50 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="text-amber-300 font-semibold">{suggestion.food_name}</h4>
                        <span className="text-emerald-200 text-sm">{suggestion.amount_grams}g</span>
                      </div>
                      <div className="text-sm text-emerald-300 mb-2">
                        {suggestion.calories} cal | {suggestion.protein}g P | {suggestion.carbs}g C | {suggestion.fat}g F
                      </div>
                      <p className="text-xs text-emerald-400 mb-3">{suggestion.reason}</p>
                      <button
                        onClick={() => addSuggestionToMeal(suggestion)}
                        className="w-full bg-amber-500 hover:bg-amber-600 text-emerald-900 font-semibold py-2 px-4 rounded text-sm transition-all duration-300"
                      >
                        Add to Meal
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Today's Meals */}
            <div className="lg:col-span-2 bg-emerald-800/30 backdrop-blur-md rounded-2xl p-6 shadow-2xl border border-emerald-700/50">
              <h2 className="text-2xl font-bold text-amber-400 mb-4">🍽️ Today's Meals</h2>
              
              {dailySummary.meals.length === 0 ? (
                <p className="text-emerald-200 text-center py-8">No meals logged yet today. Start by adding your first meal!</p>
              ) : (
                <div className="space-y-4">
                  {dailySummary.meals.map((meal, index) => (
                    <div key={index} className="bg-emerald-900/50 rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="text-amber-300 font-semibold">{meal.food_name}</h3>
                          <p className="text-emerald-200 text-sm capitalize">{meal.meal_type} • {meal.amount_grams}g</p>
                        </div>
                        <div className="text-right">
                          <p className="text-white font-semibold">{Math.round(meal.calories)} cal</p>
                          <p className="text-emerald-300 text-sm">
                            {Math.round(meal.protein)}g P | {Math.round(meal.carbs)}g C | {Math.round(meal.fat)}g F
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Add Meal View */}
        {currentView === 'add-meal' && (
          <div className="bg-emerald-800/30 backdrop-blur-md rounded-2xl p-6 shadow-2xl border border-emerald-700/50">
            <h2 className="text-2xl font-bold text-amber-400 mb-6">➕ Add New Meal</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-emerald-200 mb-2">Food Name</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={mealEntry.food_name}
                    onChange={(e) => setMealEntry({...mealEntry, food_name: e.target.value})}
                    className="flex-1 px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white placeholder-emerald-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
                    placeholder="e.g. Chicken Breast"
                  />
                  <button
                    onClick={() => lookupFood(mealEntry.food_name)}
                    disabled={loading || !mealEntry.food_name}
                    className="bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-600 hover:to-amber-500 text-emerald-900 font-semibold py-3 px-6 rounded-lg transition-all duration-300 disabled:opacity-50"
                  >
                    {loading ? '⏳' : '🔍 Lookup'}
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Meal Type</label>
                <select
                  value={mealEntry.meal_type}
                  onChange={(e) => setMealEntry({...mealEntry, meal_type: e.target.value})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                  <option value="breakfast">Breakfast</option>
                  <option value="lunch">Lunch</option>
                  <option value="dinner">Dinner</option>
                  <option value="snack">Snack</option>
                </select>
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Amount (grams)</label>
                <input
                  type="number"
                  value={mealEntry.amount_grams}
                  onChange={(e) => setMealEntry({...mealEntry, amount_grams: parseFloat(e.target.value)})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Calories</label>
                <input
                  type="number"
                  value={mealEntry.calories}
                  onChange={(e) => setMealEntry({...mealEntry, calories: parseFloat(e.target.value)})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Protein (g)</label>
                <input
                  type="number"
                  value={mealEntry.protein}
                  onChange={(e) => setMealEntry({...mealEntry, protein: parseFloat(e.target.value)})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Carbs (g)</label>
                <input
                  type="number"
                  value={mealEntry.carbs}
                  onChange={(e) => setMealEntry({...mealEntry, carbs: parseFloat(e.target.value)})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              
              <div>
                <label className="block text-emerald-200 mb-2">Fat (g)</label>
                <input
                  type="number"
                  value={mealEntry.fat}
                  onChange={(e) => setMealEntry({...mealEntry, fat: parseFloat(e.target.value)})}
                  className="w-full px-4 py-3 bg-emerald-900/50 border border-emerald-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
            </div>
            
            <div className="mt-6 flex justify-center">
              <button
                onClick={addMealEntry}
                className="bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-600 hover:to-amber-500 text-emerald-900 font-bold py-4 px-8 rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg"
              >
                Add Meal Entry 🍽️
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;