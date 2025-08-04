from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import os
from datetime import datetime
from ibm_watson import AssistantV2, NaturalLanguageUnderstandingV1
from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions, SentimentOptions, ConceptsOptions
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from cloudant.client import Cloudant
import uuid
from dotenv import load_dotenv
import logging
# Load environment variables
load_dotenv()
app = Flask(__name__)
CORS(app)
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# IBM Watson Configuration
WATSON_NLU_API_KEY = os.getenv('WATSON_NLU_API_KEY')
WATSON_NLU_URL = os.getenv('WATSON_NLU_URL')
WATSON_ASSISTANT_API_KEY = os.getenv('WATSON_ASSISTANT_API_KEY')
WATSON_ASSISTANT_URL = os.getenv('WATSON_ASSISTANT_URL')
WATSON_ASSISTANT_ID = os.getenv('WATSON_ASSISTANT_ID')
# Cloudant Configuration
CLOUDANT_USERNAME = os.getenv('ae6dd67d-c714-4782-bc29-a9834fac5fe5-bluemix')
CLOUDANT_URL = os.getenv('https://ae6dd67d-c714-4782-bc29-a9834fac5fe5-bluemix.cloudantnosqldb.appdomain.cloud')
CLOUDANT_API_KEY = os.getenv('BHKOCkHLi2mQAcPvFiuFUabjcDgyl66aszDcmA8JeEAy')
class IBMWatsonNutritionAssistant:
  def __init__(self):
    logger.info("Initializing IBM Watson Nutrition Assistant...")

    # Initialize Watson NLU
    self.nlu = None
    try:
      if WATSON_NLU_API_KEY and WATSON_NLU_URL:
        nlu_authenticator = IAMAuthenticator(WATSON_NLU_API_KEY)
        self.nlu = NaturalLanguageUnderstandingV1(
          version='2022-04-07',
          authenticator=nlu_authenticator
        )
        self.nlu.set_service_url(WATSON_NLU_URL)
        logger.info("✅ Watson NLU initialized successfully")
      else:
        logger.warning("❌Watson NLU credentials not provided")
    except Exception as e:
      logger.error(f"❌Watson NLU initialization error: {e}")
    # Initialize Watson Assistant
    self.assistant = None
    self.assistant_id = None
    try:
      if WATSON_ASSISTANT_API_KEY and WATSON_ASSISTANT_URL and WATSON_ASSISTANT_ID:
        assistant_authenticator = IAMAuthenticator(WATSON_ASSISTANT_API_KEY)
        self.assistant = AssistantV2(
          version='2023-06-15',
          authenticator=assistant_authenticator
        )
        self.assistant.set_service_url(WATSON_ASSISTANT_URL)
        self.assistant_id = WATSON_ASSISTANT_ID
        logger.info("✅Watson Assistant initialized successfully")
      else:
        logger.warning("❌Watson Assistant credentials not provided")
    except Exception as e:
      logger.error(f"❌Watson Assistant initialization error: {e}")
    # Initialize Cloudant
    self.cloudant_client = None
    try:
      if CLOUDANT_USERNAME and CLOUDANT_URL and CLOUDANT_API_KEY:
        cloudant_authenticator = IAMAuthenticator(CLOUDANT_API_KEY)
        self.cloudant_client = Cloudant(
          CLOUDANT_USERNAME,
          None,
          url=CLOUDANT_URL,
          authenticator=cloudant_authenticator,
          connect=True
        )
        self.init_databases()
        logger.info("✅Cloudant initialized successfully")
      else:
        logger.warning("❌Cloudant credentials not provided")
    except Exception as e:
      logger.error(f"❌Cloudant initialization error: {e}")
    # Enhanced food database
    self.food_database = {
       'pizza': {
              'calories': 285, 'protein': 12, 'carbs': 36, 'fat': 10, 'fiber': 2, 'sodium': 640,
              'category': 'fast_food', 'healthiness': 'moderate'
          },
          'chicken breast': {
              'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6, 'fiber': 0, 'sodium': 74,
              'category': 'protein', 'healthiness': 'high'
          },
          'grilled chicken': {
              'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6, 'fiber': 0, 'sodium': 74,
              'category': 'protein', 'healthiness': 'high'
          },
          'chicken': {
              'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6, 'fiber': 0, 'sodium': 74,
              'category': 'protein', 'healthiness': 'high'
          },
          'salad': {
              'calories': 150, 'protein': 8, 'carbs': 12, 'fat': 9, 'fiber': 5, 'sodium': 200,
              'category': 'vegetables', 'healthiness': 'high'
          },
          'quinoa': {
              'calories': 222, 'protein': 8, 'carbs': 39, 'fat': 3.6, 'fiber': 5, 'sodium': 13,
              'category': 'grains', 'healthiness': 'high'
          },
          'salmon': {
              'calories': 208, 'protein': 22, 'carbs': 0, 'fat': 12, 'fiber': 0, 'sodium': 59,
              'category': 'protein', 'healthiness': 'high'
          },
          'broccoli': {
              'calories': 34, 'protein': 3, 'carbs': 7, 'fat': 0.4, 'fiber': 3, 'sodium': 33,
              'category': 'vegetables', 'healthiness': 'high'
          },
          'avocado': {
              'calories': 160, 'protein': 2, 'carbs': 9, 'fat': 15, 'fiber': 7, 'sodium': 7,
              'category': 'healthy_fats', 'healthiness': 'high'
          },
          'rice': {
              'calories': 130, 'protein': 2.7, 'carbs': 28, 'fat': 0.3, 'fiber': 0.4, 'sodium': 1,
              'category': 'grains', 'healthiness': 'moderate'
          },
          'brown rice': {
              'calories': 112, 'protein': 2.6, 'carbs': 23, 'fat': 0.9, 'fiber': 1.8, 'sodium': 1,
              'category': 'grains', 'healthiness': 'high'
          },
          'pasta': {
              'calories': 220, 'protein': 8, 'carbs': 44, 'fat': 1.3, 'fiber': 3, 'sodium': 6,
              'category': 'grains', 'healthiness': 'moderate'
          },
          'burger': {
              'calories': 540, 'protein': 25, 'carbs': 40, 'fat': 31, 'fiber': 3, 'sodium': 1040,
              'category': 'fast_food', 'healthiness': 'low'
          },
          'eggs': {
              'calories': 155, 'protein': 13, 'carbs': 1.1, 'fat': 11, 'fiber': 0, 'sodium': 124,
              'category': 'protein', 'healthiness': 'high'
          },
          'oatmeal': {
              'calories': 389, 'protein': 17, 'carbs': 66, 'fat': 7, 'fiber': 11, 'sodium': 2,
              'category': 'grains', 'healthiness': 'high'
          },
          'yogurt': {
              'calories': 100, 'protein': 10, 'carbs': 6, 'fat': 5, 'fiber': 0, 'sodium': 46,
              'category': 'dairy', 'healthiness': 'high'
          },
          'greek yogurt': {
              'calories': 130, 'protein': 15, 'carbs': 6, 'fat': 5, 'fiber': 0, 'sodium': 50,
              'category': 'dairy', 'healthiness': 'high'
          },
          'banana': {
              'calories': 89, 'protein': 1.1, 'carbs': 23, 'fat': 0.3, 'fiber': 2.6, 'sodium': 1,
              'category': 'fruits', 'healthiness': 'high'
          },
          'apple': {
              'calories': 52, 'protein': 0.3, 'carbs': 14, 'fat': 0.2, 'fiber': 2.4, 'sodium': 1,
              'category': 'fruits', 'healthiness': 'high'
          },
          'spinach': {
              'calories': 23, 'protein': 2.9, 'carbs': 3.6, 'fat': 0.4, 'fiber': 2.2, 'sodium': 79,
              'category': 'vegetables', 'healthiness': 'high'
          },
          'sweet potato': {
              'calories': 86, 'protein': 1.6, 'carbs': 20, 'fat': 0.1, 'fiber': 3, 'sodium': 5,
              'category': 'vegetables', 'healthiness': 'high'
          },
          'almonds': {
              'calories': 579, 'protein': 21, 'carbs': 22, 'fat': 50, 'fiber': 12, 'sodium': 1,
              'category': 'nuts', 'healthiness': 'high'
          },
          'tuna': {
              'calories': 144, 'protein': 30, 'carbs': 0, 'fat': 1, 'fiber': 0, 'sodium': 39,
              'category': 'protein', 'healthiness': 'high'
          }
      }
    self.chat_sessions = {}
def init_databases(self):
   try:
             
          # Create databases if they don't exist
          if 'user_profiles' not in self.cloudant_client.all_dbs():
              self.user_profiles_db = self.cloudant_client.create_database('user_profiles')
          else:
              self.user_profiles_db = self.cloudant_client['user_profiles']
          
          if 'nutrition_data' not in self.cloudant_client.all_dbs():
              self.nutrition_data_db = self.cloudant_client.create_database('nutrition_data')
          else:
              self.nutrition_data_db = self.cloudant_client['nutrition_data']
              
          if 'chat_sessions' not in self.cloudant_client.all_dbs():
              self.chat_sessions_db = self.cloudant_client.create_database('chat_sessions')
          else:
              self.chat_sessions_db = self.cloudant_client['chat_sessions']
              
   except Exception as e:
      logger.error(f"Database initialization error: {e}")
def analyze_food_with_nlu(self, food_description):
   if not self.nlu:
      logger.info("Watson NLU not available, using fallback analysis")
      return self.fallback_food_analysis(food_description)
   try:
      logger.info(f"Analyzing food with Watson NLU: {food_description}")
      response = self.nlu.analyze(
         text=food_description,
         features=Features(
            entities=EntitiesOptions(limit=10),
            keywords=KeywordsOptions(limit=10),
            sentiment=SentimentOptions(),
            concepts=ConceptsOptions(limit=5)
         )
      ).get_result()
      logger.info("Watson NLU analysis completed successfully")
# Extract food entities and keywords
      food_items = []
# Check entities
      if 'entities' in response:
         for entity in response['entities']:
            entity_text = entity['text'].lower()
            logger.info(f"Found entity: {entity_text}")
            if any(food in entity_text or entity_text in food for food in self.food_database.keys()):
               food_items.append(entity_text)
# Check keywords
      if 'keywords' in response:
         for keyword in response['keywords']:
            keyword_text = keyword['text'].lower()
            logger.info(f"Found keyword: {keyword_text}")
            if any(food in keyword_text or keyword_text in food for food in self.food_database.keys()):
               food_items.append(keyword_text)
# Direct text matching as fallback
      food_lower = food_description.lower()
      for food_name in self.food_database.keys():
         if food_name in food_lower and food_name not in food_items:
            food_items.append(food_name)
            logger.info(f"Direct match found: {food_name}")
# Get sentiment and concepts for analysis
      sentiment_score = 0
      if 'sentiment' in response and 'document' in response['sentiment']:
         sentiment_score = response['sentiment']['document'].get('score', 0)
      concepts = response.get('concepts', [])
      return self.get_nutrition_from_items(food_items, sentiment_score, food_description, concepts)
   except Exception as e:
      logger.error(f"Watson NLU analysis error: {e}")
      return self.fallback_food_analysis(food_description)
def get_nutrition_from_items(self, food_items, sentiment_score, original_description, 
concepts=None):
   total_nutrition = {
      'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 
      'fiber': 0, 'sodium': 0
   }
   matched_foods = []
   for item in food_items:
      best_match = None
      best_score = 0
      for food_name, nutrition in self.food_database.items():
         if food_name in item or item in food_name:
            score = len(set(food_name.split()) & set(item.split()))
            if score > best_score:
               best_score = score
               best_match = food_name
         elif food_name == item:
            best_match = food_name
            break
      if best_match and best_match not in matched_foods:
         matched_foods.append(best_match)
         nutrition = self.food_database[best_match]
         for key in ['calories', 'protein', 'carbs', 'fat', 'fiber', 'sodium']:
            total_nutrition[key] += nutrition.get(key, 0)
   if not matched_foods:
      return self.fallback_food_analysis(original_description)
# Generate analysis
   analysis = self.generate_smart_analysis(matched_foods, sentiment_score, total_nutrition, 
concepts)
   return {
      'nutrition': total_nutrition,
      'analysis': analysis,
      'matched_foods': matched_foods,
      'recommendations': self.get_ai_recommendations(total_nutrition, matched_foods),
      'watson_insights': {
         'sentiment_score': sentiment_score,
         'concepts': concepts[:3] if concepts else []
       }
   }
def generate_smart_analysis(self, matched_foods, sentiment_score, nutrition, concepts=None):
   analysis_parts = []
# Calorie assessment
   if nutrition['calories'] > 500:
      analysis_parts.append("This is a high-calorie meal")
   elif nutrition['calories'] < 200:
      analysis_parts.append("This is a low-calorie option")
   else:
      analysis_parts.append("This meal has moderate calories")
# Protein assessment
   if nutrition['protein'] > 25:
      analysis_parts.append("excellent protein content for muscle maintenance")
   elif nutrition['protein'] < 10:
      analysis_parts.append("consider adding more protein sources")
# Fiber assessment
   if nutrition['fiber'] > 8:
      analysis_parts.append("high in fiber for digestive health")
   elif nutrition['fiber'] < 3:
      analysis_parts.append("low in fiber - consider adding vegetables or whole grains")
# Sodium assessment
   if nutrition['sodium'] > 600:
      analysis_parts.append("high sodium content - watch your salt intake")
# Food category analysis
   categories = []
   healthiness_scores = []
   for food in matched_foods:
      if food in self.food_database:
         category = self.food_database[food]['category']
         if category not in categories:
            categories.append(category)
         healthiness = self.food_database[food]['healthiness']
         if healthiness == 'high':
            healthiness_scores.append(3)
         elif healthiness == 'moderate':
            healthiness_scores.append(2)
         else:
            healthiness_scores.append(1)
   if 'vegetables' in categories:
      analysis_parts.append("includes nutritious vegetables")
   if 'fast_food' in categories:
      analysis_parts.append("contains processed foods - balance with whole foods")
   if 'protein' in categories:
      analysis_parts.append("good protein sources included")
# Overall healthiness assessment
   if healthiness_scores:
      avg_healthiness = sum(healthiness_scores) / len(healthiness_scores)
      if avg_healthiness >= 2.5:
         analysis_parts.append("overall a nutritious choice")
      elif avg_healthiness >= 2:
         analysis_parts.append("moderately healthy option")
      else:
         analysis_parts.append("consider healthier alternatives")
# Use Watson concepts if available
   if concepts:
      for concept in concepts[:2]:
         concept_text = concept.get('text', '').lower()
         if 'healthy' in concept_text or 'nutrition' in concept_text:
            analysis_parts.append("appears to align with healthy eating patterns")
         elif 'processed' in concept_text or 'fast' in concept_text:
            analysis_parts.append("may contain processed ingredients")
   return ". ".join(analysis_parts).capitalize() + "."
def get_ai_recommendations(self, nutrition, matched_foods):
   recommendations = []
# Nutritional recommendations
   if nutrition['sodium'] > 500:
      recommendations.append("Consider reducing sodium by using herbs and spices instead of salt")
   if nutrition['fiber'] < 5:
      recommendations.append("Add more fiber with vegetables, fruits, or whole grains")
   if nutrition['protein'] < 15:
      recommendations.append("Include lean protein sources like chicken, fish, or legumes")
   if nutrition['calories'] > 600:
      recommendations.append("Consider portion control or splitting this meal")
# Category-based recommendations
   categories = [self.food_database[food]['category'] for food in matched_foods if food in self.food_database]
   if 'vegetables' not in categories:
      recommendations.append("Add colorful vegetables for vitamins and minerals")
   if 'healthy_fats' not in categories and nutrition['fat'] < 10:
      recommendations.append("Include healthy fats like avocado, nuts, or olive oil")
   if 'fruits' not in categories:
      recommendations.append("Consider adding fruits for natural vitamins and antioxidants")
# Food-specific recommendations
   if 'pizza' in matched_foods:
      recommendations.append("Try thin crust pizza with vegetable toppings for a healthier option")
   elif 'burger' in matched_foods:
      recommendations.append("Consider a turkey burger with whole grain bun and extra vegetables")
   elif any('salad' in food for food in matched_foods):
      recommendations.append("Great choice! Add nuts or seeds for healthy fats and protein")
   return recommendations[:5]  # Limit to 5 recommendations
def fallback_food_analysis(self, food_description):
  logger.info("Using fallback food analysis")
  food_lower = food_description.lower()
# Try to match foods from description
  matched_foods = []
  total_nutrition = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sodium': 0}
  for food_name, nutrition in self.food_database.items():
     if food_name in food_lower:
        matched_foods.append(food_name)
        for key in total_nutrition.keys():
           total_nutrition[key] += nutrition.get(key, 0)
  if matched_foods:
     return {
        'nutrition': total_nutrition,
        'analysis': f"Based on your description, this appears to contain {', '.join(matched_foods)}. " + self.get_food_analysis_text(matched_foods[0], total_nutrition),
        'matched_foods': matched_foods,
        'recommendations': self.get_ai_recommendations(total_nutrition, matched_foods)
     }
# Default response for unrecognized foods
  default_nutrition = {
     'calories': 250, 'protein': 15, 'carbs': 30, 'fat': 8, 'fiber': 4, 'sodium': 300
  }
  return {
     'nutrition': default_nutrition,
     'analysis': "Based on your description, this appears to be a balanced meal. Consider portion sizes and cooking methods for optimal nutrition.",
     'matched_foods': ['general meal'],
     'recommendations': ["Focus on whole foods", "Balance your macronutrients", "Stay hydrated"]
  }
def get_food_analysis_text(self, food_name, nutrition):
  analyses = {
     'pizza': 'High in calories and sodium. Consider thin crust with vegetables for a healthier option.',
     'chicken breast': 'Excellent lean protein source. Great for muscle building and weight management.',
     'grilled chicken': 'Excellent lean protein source. Great for muscle building and weight management.',
     'chicken': 'Excellent lean protein source. Great for muscle building and weight management.',
     'salad': 'Low calorie, high fiber option. Add protein and healthy fats for a complete meal.',
     'quinoa': 'Complete protein grain, rich in fiber and minerals. Excellent for sustained energy.',
     'salmon': 'Rich in omega-3 fatty acids and high-quality protein. Great for heart and brain health.',
     'broccoli': 'Low calorie, high in vitamins C and K, and fiber. Excellent for overall health.',
     'avocado': 'Rich in healthy monounsaturated fats and fiber. Great for heart health and satiety.',
     'eggs': 'Complete protein with essential amino acids. Great for breakfast or any meal.',
     'oatmeal': 'High fiber whole grain that helps lower cholesterol and provides sustained energy.',
     'greek yogurt': 'High protein dairy option with probiotics for digestive health.'
  }
  return analyses.get(food_name, 'Nutritious food choice with balanced macronutrients.')
def chat_with_watson(self, message, session_id=None):
   if not self.assistant:
      logger.info("Watson Assistant not available, using fallback")
      return self.fallback_chat_response(message)
   try:
      logger.info(f"Sending message to Watson Assistant: {message}")
      # Create session if not provided
      if not session_id:
         session_response = self.assistant.create_session(
            assistant_id=self.assistant_id
         ).get_result()
         session_id = session_response['session_id']
         logger.info(f"Created new session: {session_id}")
# Send message to Watson Assistant
      response = self.assistant.message(
         assistant_id=self.assistant_id,
         session_id=session_id,
         input={
            'message_type': 'text',
            'text': message
         }
      ).get_result()
      logger.info("Watson Assistant response received")
# Extract response text
      assistant_response = "I'm here to help with your nutrition questions!"
      if response.get('output', {}).get('generic'):
         for generic_response in response['output']['generic']:
            if generic_response.get('response_type') == 'text':
               assistant_response = generic_response.get('text', assistant_response)
               break
      # Store chat in Cloudant
      self.store_chat_session(session_id, message, assistant_response)
      return {
         'response': assistant_response,
         'session_id': session_id
      }
   except Exception as e:
      logger.error(f"Watson Assistant error: {e}")
      return self.fallback_chat_response(message)
def fallback_chat_response(self, message):
   message_lower = message.lower()
   nutrition_responses = {
      'protein': "Protein is essential for muscle building and repair. Good sources include chicken, "
      "fish, eggs, beans, and nuts. Aim for 0.8-1g per kg of body weight daily for general health, or 1.6-2.2g "
      "per kg for muscle building.",
      'carbs': "Carbohydrates provide energy for your body and brain. Choose complex carbs like "
      "whole grains, fruits, and vegetables over simple sugars. They should make up 45-65% of your daily "
      "calories.",
      'fat': "Healthy fats are important for hormone production and nutrient absorption. Include "
      "sources like avocados, nuts, olive oil, and fatty fish. Aim for 20-35% of your daily calories from healthy "
      "fats.",
      'weight loss': "For weight loss, create a moderate calorie deficit of 300-500 calories daily "
      "through diet and exercise. Focus on whole foods, portion control, staying hydrated, and getting "
      "adequate sleep.",
      'muscle gain': "For muscle gain, eat adequate protein (1.6-2.2g per kg body weight), maintain "
      "a slight calorie surplus, and engage in resistance training. Include protein at every meal and consider "
      "post-workout nutrition.",
      'vitamins': "Vitamins are essential micronutrients. Get them from a varied diet rich in colorful "
      "fruits, vegetables, whole grains, and lean proteins. A rainbow of foods ensures diverse vitamin "
      "intake.",
      'water': "Stay hydrated by drinking 8-10 glasses of water daily, more if you're active or in hot "
      "weather. Water helps with digestion, nutrient transport, and temperature regulation.",
      'meal planning': "Plan balanced meals with protein, complex carbs, healthy fats, and plenty of "
      "vegetables. Prep meals in advance for consistency. Include variety to ensure all nutrient needs are "
      "met.",
      'hello': "Hello! I'm your AI nutrition assistant powered by IBM Watson. I can help you with meal "
      "planning, nutritional advice, and healthy eating tips. What would you like to know?",
      'help': "I can help you with nutrition questions, meal planning, weight management, healthy "
      "eating advice, and food analysis. Just ask me anything about food and nutrition!",
      'calories': "Calories are units of energy from food. Your daily needs depend on age, gender, "
      "weight, height, and activity level. Focus on nutrient-dense calories rather than empty calories from "
      "processed foods.",
      'fiber': "Fiber aids digestion and helps you feel full. Adults need 25-35g daily. Good sources "
      "include fruits, vegetables, whole grains, and legumes. Increase fiber intake gradually to avoid "
      "digestive discomfort.",
      'sodium': "Limit sodium to less than 2300mg daily (1500mg if you have high blood pressure). "
      "Use herbs and spices instead of salt. Read food labels as processed foods are often high in sodium.",
      'sugar': "Limit added sugars to less than 10% of daily calories. Natural sugars from fruits come "
      "with fiber and nutrients. Avoid sugary drinks and processed foods with added sugars."
    }
   for keyword, response in nutrition_responses.items():
      if keyword in message_lower:
         return {'response': response, 'session_id': str(uuid.uuid4())}
      return {
         'response': "I'm your nutrition assistant! I can help you with healthy eating, meal planning,macronutrients, weight management, and food analysis. What specific nutrition topic would you like to discuss?",
         'session_id': str(uuid.uuid4())
      }
def store_chat_session(self, session_id, user_message, assistant_response):
   if not self.cloudant_client:
      return
   try:
      chat_doc = {
         '_id': f"chat_{session_id}_{datetime.now().isoformat()}_{uuid.uuid4()}",
         'session_id': session_id,
         'timestamp': datetime.now().isoformat(),
         'user_message': user_message,
         'assistant_response': assistant_response
      }
      self.chat_sessions_db.create_document(chat_doc)
      logger.info("Chat session stored successfully")
   except Exception as e:
      logger.error(f"Error storing chat session: {e}")
def store_user_profile(self, profile_data):
   if not self.cloudant_client:
      return str(uuid.uuid4())
   try:
      profile_id = str(uuid.uuid4())
      profile_doc = {
         '_id': profile_id,
         'timestamp': datetime.now().isoformat(),
         **profile_data
      }
      self.user_profiles_db.create_document(profile_doc)
      logger.info("User profile stored successfully")
      return profile_id
   except Exception as e:
      logger.error(f"Error storing user profile: {e}")
      return str(uuid.uuid4())
def store_nutrition_analysis(self, analysis_data):
   if not self.cloudant_client:
      return
   try:
      analysis_doc = {
      '_id': f"analysis_{datetime.now().isoformat()}_{uuid.uuid4()}",
      'timestamp': datetime.now().isoformat(),
      **analysis_data
      }
      self.nutrition_data_db.create_document(analysis_doc)
      logger.info("Nutrition analysis stored successfully")
   except Exception as e:
      logger.error(f"Error storing nutrition analysis: {e}")
# Initialize the Watson Nutrition Assistant
logger.info("Starting IBM Watson Nutrition Assistant...")
watson_assistant = IBMWatsonNutritionAssistant()
class NutritionCalculator:
   def calculate_bmi(self, weight, height):
      height_m = height / 100
      return round(weight / (height_m ** 2), 1)
   def get_bmi_category(self, bmi):
      if bmi < 18.5:
         return "Underweight"
      elif bmi < 25:
         return "Normal weight"
      elif bmi < 30:
         return "Overweight"
      else:
         return "Obese"
   def calculate_bmr(self, age, gender, weight, height):
      if gender.lower() == 'male':
         bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
      else:
         bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
      return round(bmr)
   def calculate_daily_calories(self, age, gender, weight, height, activity_level):
      bmr = self.calculate_bmr(age, gender, weight, height)
      activity_multipliers = {
         'sedentary': 1.2,
         'light': 1.375,
         'moderate': 1.55,
         'active': 1.725,
         'very-active': 1.9
      }
      multiplier = activity_multipliers.get(activity_level, 1.2)
      return round(bmr * multiplier)
   def calculate_macros(self, calories, goal):
      macro_ratios = {
         'weight-loss': {'protein': 0.35, 'carbs': 0.30, 'fat': 0.35},
         'weight-gain': {'protein': 0.25, 'carbs': 0.45, 'fat': 0.30},
         'muscle-gain': {'protein': 0.35, 'carbs': 0.40, 'fat': 0.25},
         'maintenance': {'protein': 0.30, 'carbs': 0.40, 'fat': 0.30},
         'health': {'protein': 0.30, 'carbs': 0.40, 'fat': 0.30}
      }
      ratios = macro_ratios.get(goal, macro_ratios['health'])
      protein_grams = round((calories * ratios['protein']) / 4)
      carbs_grams = round((calories * ratios['carbs']) / 4)
      fat_grams = round((calories * ratios['fat']) / 9)
      return {
         'protein': protein_grams,
         'carbs': carbs_grams,
         'fat': fat_grams
      }

   def calculate_water_needs(self, weight, activity_level):
      base_water = weight * 0.035  # 35ml per kg
      activity_multipliers = {
         'sedentary': 1.0,
         'light': 1.1,
         'moderate': 1.2,
         'active': 1.3,
         'very-active': 1.4
      }
      multiplier = activity_multipliers.get(activity_level, 1.0)
      return round(base_water * multiplier, 1)
# API Routes
@app.route('/')
def index():
   return render_template('index.html')
@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
   try:
      data = request.json
      message = data.get('message', '')
      session_id = data.get('session_id')
      logger.info(f"Received chat request: {message}")
      result = watson_assistant.chat_with_watson(message, session_id)
      return jsonify({
         'success': True,
         'response': result['response'],
         'session_id': result['session_id']
      })
   except Exception as e:
      logger.error(f"Chat endpoint error: {e}")
      return jsonify({
         'success': False,
         'error': str(e)
      }), 400
@app.route('/api/analyze', methods=['POST'])
def analyze_nutrition():
   try:
      data = request.json
      calculator = NutritionCalculator()
      logger.info("Received nutrition analysis request")
      # Extract user profile
      profile = {
         'age': data.get('age'),
         'gender': data.get('gender'),
         'height': data.get('height'),
         'weight': data.get('weight'),
         'activity_level': data.get('activity_level'),
         'goal': data.get('goal'),
         'diet_type': data.get('diet_type'),
         'health_conditions': data.get('health_conditions', []),
         'allergies': data.get('allergies', ''),
         'food_input': data.get('food_input', '')
      }
      # Store user profile in Cloudant
      profile_id = watson_assistant.store_user_profile(profile)
      # Calculate basic metrics
      bmi = calculator.calculate_bmi(profile['weight'], profile['height'])
      bmi_category = calculator.get_bmi_category(bmi)
      bmr = calculator.calculate_bmr(profile['age'], profile['gender'], profile['weight'], profile['height'])
      daily_calories = calculator.calculate_daily_calories(
         profile['age'], profile['gender'], profile['weight'], 
         profile['height'], profile['activity_level']
      )
      # Calculate macros
      macros = calculator.calculate_macros(daily_calories, profile['goal'])
      # Calculate water needs
      water_needs = calculator.calculate_water_needs(profile['weight'], profile['activity_level'])
      # Calculate fiber needs
      fiber_needs = 38 if profile['gender'] == 'male' and profile['age'] < 50 else \
        30 if profile['gender'] == 'male' else \
        25 if profile['age'] < 50 else 21
      
      # Analyze food with Watson NLU if provided
      food_analysis = None
      if profile['food_input']:
          logger.info(f"Analyzing food input: {profile['food_input']}")
          food_analysis = watson_assistant.analyze_food_with_nlu(profile['food_input'])
      
      # Generate meal plan based on goal and dietary preferences
      meal_plans = {
         'weight-loss': {
              'breakfast': 'Greek yogurt (150g) with mixed berries (100g) and almonds (15g) - 320 cal',
              'lunch': 'Grilled chicken breast (120g) with quinoa salad (150g) and vegetables - 450 cal',
              'dinner': 'Baked salmon (100g) with roasted vegetables (200g) and sweet potato (100g) - 380 cal',
              'snacks': 'Apple with 1 tbsp almond butter - 150 cal'
          },
          'weight-gain': {
              'breakfast': 'Oatmeal (80g) with banana, nuts (30g), and protein powder (30g) - 520 cal',
              'lunch': 'Turkey and avocado wrap with sweet potato fries - 650 cal',
              'dinner': 'Lean beef (150g) with brown rice (150g) and steamed broccoli - 580 cal',
              'snacks': 'Greek yogurt with granola and honey - 250 cal'
          },
          'muscle-gain': {
              'breakfast': 'Scrambled eggs (3 eggs) with spinach and whole grain toast (2 slices) - 480 cal',
              'lunch': 'Grilled chicken breast (150g) with quinoa (100g) and mixed vegetables - 550 cal',
              'dinner': 'Lean ground turkey (120g) with sweet potato (150g) and green beans - 520 cal',
              'snacks': 'Protein shake with banana - 300 cal'
          },
          'maintenance': {
              'breakfast': 'Smoothie bowl with fruits, granola, and Greek yogurt - 420 cal',
              'lunch': 'Mediterranean bowl with chickpeas, feta, and vegetables - 480 cal',
              'dinner': 'Grilled fish (120g) with quinoa (100g) and roasted vegetables - 450 cal',
              'snacks': 'Mixed nuts and dried fruit - 200 cal'
          }
      }
      
      meal_plan = meal_plans.get(profile['goal'], meal_plans['maintenance'])
      
      # Generate personalized recommendations
      recommendations = []
      
      # BMI-based recommendations
      if bmi < 18.5:
          recommendations.append({
             'title': 'Healthy Weight Gain',
             'text': 'Include calorie-dense, nutrient-rich foods like nuts, avocados, and lean proteins. Consider eating more frequent meals.'
          })
      elif bmi > 25:
         recommendations.append({
            'title': 'Weight Management',
            'text': 'Focus on portion control and increase physical activity. Choose whole foods over processed options and practice mindful eating.'
          })
      else:
         recommendations.append({
            'title': 'Maintain Healthy Weight',
            'text': 'Continue your current approach with balanced nutrition and regular physical activity.'
         })
      # Activity-based recommendations
      if profile['activity_level'] == 'sedentary':
         recommendations.append({
            'title': 'Increase Physical Activity',
            'text': 'Try to incorporate at least 30 minutes of moderate exercise daily. Start with walking and gradually increase intensity.'
         })
      # Health condition recommendations
      health_conditions = profile.get('health_conditions', [])
      if 'diabetes' in health_conditions:
         recommendations.append({
            'title': 'Blood Sugar Management',
            'text': 'Focus on complex carbohydrates and pair carbs with protein to stabilize blood sugar levels. Monitor portion sizes.'
         })
      if 'hypertension' in health_conditions:
         recommendations.append({
            'title': 'Sodium Reduction',
            'text': 'Limit sodium intake to less than 2300mg daily. Use herbs and spices for flavoring instead of salt.'
         })
      if 'high-cholesterol' in health_conditions:
         recommendations.append({
            'title': 'Heart-Healthy Eating',
            'text': 'Include omega-3 rich foods like salmon and walnuts. Limit saturated fats and increase soluble fiber intake.'
         })
      # General recommendations
      recommendations.append({
         'title': 'Daily Hydration',
         'text': f'Aim for {water_needs} liters of water daily based on your body weight and activity level.'
      })
      recommendations.append({
         'title': 'Meal Timing',
         'text': 'Eat regular meals every 3-4 hours to maintain stable energy levels and metabolism.'
      })
      # Diet-specific recommendations
      diet_type = profile.get('diet_type', '')
      if diet_type == 'vegetarian':
         recommendations.append({
            'title': 'Vegetarian Nutrition',
            'text': 'Ensure adequate protein from legumes, nuts, and dairy. Consider B12 supplementation.'
         })
      elif diet_type == 'vegan':
         recommendations.append({
            'title': 'Vegan Nutrition',
            'text': 'Focus on protein combining and consider B12, iron, and omega-3 supplementation.'
         })
      elif diet_type == 'keto':
         recommendations.append({
            'title': 'Ketogenic Diet',
            'text': 'Maintain proper electrolyte balance and include plenty of low-carb vegetables for micronutrients.'
         })
# Store analysis in Cloudant
      analysis_data = {
         'profile_id': profile_id,
         'bmi': bmi,
         'bmi_category': bmi_category,
         'bmr': bmr,
         'daily_calories': daily_calories,
         'macros': macros,
         'water_needs': water_needs,
         'food_analysis': food_analysis
      }
      watson_assistant.store_nutrition_analysis(analysis_data)
      response = {
         'success': True,
         'data': {
            'profile_id': profile_id,
            'bmi': bmi,
            'bmi_category': bmi_category,
            'bmr': bmr,
            'daily_calories': daily_calories,
            'macros': macros,
            'fiber_needs': fiber_needs,
            'water_needs': water_needs,
            'meal_plan': meal_plan,
            'food_analysis': food_analysis,
            'recommendations': recommendations,
            'profile': profile
         }
      }
      logger.info("Nutrition analysis completed successfully")
      return jsonify(response)
   except Exception as e:
      logger.error(f"Analysis error: {e}")
      return jsonify({
         'success': False,
         'error': str(e)
      }), 400
@app.route('/api/health', methods=['GET'])
def health_check():
   services_status = {
      'watson_nlu': watson_assistant.nlu is not None,
      'watson_assistant': watson_assistant.assistant is not None,
      'cloudant': watson_assistant.cloudant_client is not None
   }
   return jsonify({
      'status': 'healthy',
      'services': services_status,
      'timestamp': datetime.now().isoformat()
   })
@app.route('/api/food-database', methods=['GET'])
def get_food_database():
   foods = list(watson_assistant.food_database.keys())
   return jsonify({
      'success': True,
      'foods': sorted(foods),
      'count': len(foods)
   })
if __name__ == '__main__':
   logger.info("🚀Starting IBM Watson Nutrition Assistant Server...")
   logger.info("📊Services Status:")
   logger.info(f"   Watson NLU: {'✅Connected' if watson_assistant.nlu else '❌Not Connected'}")
   logger.info(f"   Watson Assistant: {'✅Connected' if watson_assistant.assistant else '❌Not Connected'}")
   logger.info(f"   Cloudant: {'✅Connected' if watson_assistant.cloudant_client else '❌Not Connected'}")
   logger.info("🌐Server running on http://localhost:5000")
   app.run(debug=True, host='0.0.0.0', port=8080)