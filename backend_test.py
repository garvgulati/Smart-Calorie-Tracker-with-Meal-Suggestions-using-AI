#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, date
from typing import Dict, Any

class SmartMacroTrackerAPITester:
    def __init__(self, base_url="https://2c88d078-546b-48e7-8491-936fbe4388a6.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.today = date.today().isoformat()

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, data: Dict[Any, Any] = None) -> tuple:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_create_user(self) -> bool:
        """Test user creation"""
        user_data = {
            "name": "Test User",
            "age": 30,
            "gender": "male",
            "activity_level": "moderate",
            "goal": "maintenance",
            "daily_calorie_target": 2000,
            "macro_split": {"protein": 30, "carbs": 40, "fat": 30},
            "dietary_preferences": []
        }
        
        success, response = self.run_test(
            "Create User",
            "POST",
            "users",
            200,
            data=user_data
        )
        
        if success and 'id' in response:
            self.user_id = response['id']
            print(f"   Created user with ID: {self.user_id}")
            return True
        return False

    def test_get_user(self) -> bool:
        """Test getting user by ID"""
        if not self.user_id:
            print("❌ No user ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get User by ID",
            "GET",
            f"users/{self.user_id}",
            200
        )
        
        if success and response.get('name') == 'Test User':
            print(f"   Retrieved user: {response.get('name')}")
            return True
        return False

    def test_get_all_users(self) -> bool:
        """Test getting all users"""
        success, response = self.run_test(
            "Get All Users",
            "GET",
            "users",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} users")
            return True
        return False

    def test_populate_food_database(self) -> bool:
        """Test populating food database"""
        success, response = self.run_test(
            "Populate Food Database",
            "POST",
            "populate-food-database",
            200
        )
        
        if success:
            print(f"   Response: {response.get('message', 'Success')}")
            return True
        return False

    def test_get_foods(self) -> bool:
        """Test getting all foods"""
        success, response = self.run_test(
            "Get All Foods",
            "GET",
            "foods",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} foods in database")
            return True
        return False

    def test_search_foods(self) -> bool:
        """Test food search functionality"""
        success, response = self.run_test(
            "Search Foods (chicken)",
            "GET",
            "foods/search/chicken",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} foods matching 'chicken'")
            return True
        return False

    def test_ai_food_lookup(self) -> bool:
        """Test AI food lookup"""
        lookup_data = {"food_name": "banana"}
        
        success, response = self.run_test(
            "AI Food Lookup",
            "POST",
            "ai-food-lookup",
            200,
            data=lookup_data
        )
        
        if success and 'calories_per_100g' in response:
            print(f"   Found nutrition for banana: {response.get('calories_per_100g')} cal/100g")
            return True
        elif success and 'error' in response:
            print(f"   AI returned error: {response.get('error')}")
            return True  # This is still a valid response
        return False

    def test_create_meal_entry(self) -> bool:
        """Test creating a meal entry"""
        if not self.user_id:
            print("❌ No user ID available for testing")
            return False
            
        meal_data = {
            "user_id": self.user_id,
            "food_name": "Test Chicken Breast",
            "amount_grams": 100,
            "meal_type": "lunch",
            "calories": 165,
            "protein": 31,
            "carbs": 0,
            "fat": 3.6
        }
        
        success, response = self.run_test(
            "Create Meal Entry",
            "POST",
            "meals",
            200,
            data=meal_data
        )
        
        if success and 'id' in response:
            print(f"   Created meal entry with ID: {response['id']}")
            return True
        return False

    def test_get_daily_summary(self) -> bool:
        """Test getting daily summary"""
        if not self.user_id:
            print("❌ No user ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get Daily Summary",
            "GET",
            f"daily-summary/{self.user_id}/{self.today}",
            200
        )
        
        if success and 'total_calories' in response:
            print(f"   Daily calories: {response.get('total_calories')}/{response.get('calorie_target')}")
            print(f"   Meals today: {len(response.get('meals', []))}")
            return True
        return False

    def test_ai_meal_suggestions(self) -> bool:
        """Test AI meal suggestions"""
        if not self.user_id:
            print("❌ No user ID available for testing")
            return False
            
        suggestion_data = {
            "user_id": self.user_id,
            "current_date": self.today,
            "remaining_calories": 500,
            "remaining_protein": 25,
            "remaining_carbs": 50,
            "remaining_fat": 15,
            "meal_type": "dinner",
            "dietary_preferences": []
        }
        
        success, response = self.run_test(
            "AI Meal Suggestions",
            "POST",
            "ai-meal-suggestions",
            200,
            data=suggestion_data
        )
        
        if success and 'suggestions' in response:
            suggestions = response['suggestions']
            print(f"   Got {len(suggestions)} meal suggestions")
            if suggestions:
                print(f"   First suggestion: {suggestions[0].get('food_name', 'Unknown')}")
            return True
        return False

    def test_get_meals_for_date(self) -> bool:
        """Test getting meals for a specific date"""
        if not self.user_id:
            print("❌ No user ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get Meals for Date",
            "GET",
            f"meals/{self.user_id}/{self.today}",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} meals for today")
            return True
        return False

    def run_all_tests(self) -> int:
        """Run all API tests"""
        print("🚀 Starting Smart Macro Tracker API Tests")
        print(f"📍 Testing against: {self.api_url}")
        print("=" * 60)

        # Test sequence
        tests = [
            self.test_create_user,
            self.test_get_user,
            self.test_get_all_users,
            self.test_populate_food_database,
            self.test_get_foods,
            self.test_search_foods,
            self.test_ai_food_lookup,
            self.test_create_meal_entry,
            self.test_get_daily_summary,
            self.test_ai_meal_suggestions,
            self.test_get_meals_for_date
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test failed with exception: {str(e)}")

        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    tester = SmartMacroTrackerAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())