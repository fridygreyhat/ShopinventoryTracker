"""
Gemini AI Service for ShopInventoryTracker
Provides AI-powered insights and recommendations
"""

import requests
import json
import logging
from typing import Dict, List, Any, Optional
from firebase_config import firebase_config
import os

logger = logging.getLogger(__name__)

class GeminiAIService:
    def __init__(self):
        self.api_key = os.environ.get('FIREBASE_API_KEY')
        self.project_id = os.environ.get('FIREBASE_PROJECT_ID', 'inventory-management-75a65')
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash"
        
        if not self.api_key:
            logger.warning("FIREBASE_API_KEY not found. AI features will be limited.")
    
    def _make_request(self, prompt: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Make a request to the Gemini API"""
        if not self.api_key:
            logger.error("No API key configured for Gemini AI")
            return None
            
        try:
            url = f"{self.base_url}:generateContent"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    logger.error("No candidates in Gemini response")
                    return None
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return None
    
    def generate_inventory_insights(self, inventory_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI-powered inventory insights"""
        try:
            prompt = f"""
            Analyze the following inventory data and provide actionable insights:
            
            {json.dumps(inventory_data, indent=2)}
            
            Please provide a comprehensive analysis including:
            1. Stock level analysis (overstocked, understocked, optimal levels)
            2. Reorder recommendations with specific quantities
            3. Trend analysis based on current stock levels
            4. Cost optimization suggestions
            5. Risk assessment for stock-outs or excess inventory
            
            Format your response as JSON with the following structure:
            {{
                "stock_analysis": {{
                    "overstocked_items": [],
                    "understocked_items": [],
                    "optimal_items": []
                }},
                "reorder_recommendations": [],
                "trends": {{}},
                "cost_optimization": [],
                "risk_assessment": {{}}
            }}
            """
            
            response = self._make_request(prompt)
            if response:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    return {"raw_response": response, "status": "success"}
            else:
                return {"error": "Failed to generate insights", "status": "error"}
                
        except Exception as e:
            logger.error(f"Error generating inventory insights: {str(e)}")
            return {"error": str(e), "status": "error"}
    
    def generate_sales_forecast(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI-powered sales forecasting"""
        try:
            prompt = f"""
            Based on the following sales data, provide sales forecasting and analysis:
            
            {json.dumps(sales_data, indent=2)}
            
            Please analyze and provide:
            1. Sales trends over time
            2. Seasonal patterns identification
            3. Future sales predictions (next 30, 60, 90 days)
            4. Growth opportunities
            5. Performance metrics and KPIs
            
            Format as JSON:
            {{
                "trends": {{}},
                "seasonal_patterns": [],
                "forecasts": {{
                    "next_30_days": {{}},
                    "next_60_days": {{}},
                    "next_90_days": {{}}
                }},
                "growth_opportunities": [],
                "performance_metrics": {{}}
            }}
            """
            
            response = self._make_request(prompt)
            if response:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    return {"raw_response": response, "status": "success"}
            else:
                return {"error": "Failed to generate forecast", "status": "error"}
                
        except Exception as e:
            logger.error(f"Error generating sales forecast: {str(e)}")
            return {"error": str(e), "status": "error"}
    
    def generate_product_recommendations(self, customer_data: Dict[str, Any], inventory_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI-powered product recommendations"""
        try:
            prompt = f"""
            Based on customer data and available inventory, suggest product recommendations:
            
            Customer Data: {json.dumps(customer_data, indent=2)}
            Inventory Data: {json.dumps(inventory_data, indent=2)}
            
            Please provide:
            1. Personalized product recommendations for this customer
            2. Cross-selling opportunities
            3. Up-selling suggestions
            4. Seasonal recommendations
            5. Inventory turnover optimization suggestions
            
            Format as JSON:
            {{
                "personalized_recommendations": [],
                "cross_selling": [],
                "up_selling": [],
                "seasonal_recommendations": [],
                "inventory_optimization": []
            }}
            """
            
            response = self._make_request(prompt)
            if response:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    return {"raw_response": response, "status": "success"}
            else:
                return {"error": "Failed to generate recommendations", "status": "error"}
                
        except Exception as e:
            logger.error(f"Error generating product recommendations: {str(e)}")
            return {"error": str(e), "status": "error"}
    
    def generate_business_insights(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive business insights"""
        try:
            prompt = f"""
            Analyze the following business data and provide strategic insights:
            
            {json.dumps(business_data, indent=2)}
            
            Please provide:
            1. Business performance analysis
            2. Market opportunities identification
            3. Operational efficiency recommendations
            4. Financial insights and recommendations
            5. Strategic recommendations for growth
            
            Format as JSON:
            {{
                "performance_analysis": {{}},
                "market_opportunities": [],
                "operational_recommendations": [],
                "financial_insights": {{}},
                "strategic_recommendations": []
            }}
            """
            
            response = self._make_request(prompt)
            if response:
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    return {"raw_response": response, "status": "success"}
            else:
                return {"error": "Failed to generate insights", "status": "error"}
                
        except Exception as e:
            logger.error(f"Error generating business insights: {str(e)}")
            return {"error": str(e), "status": "error"}
    
    def generate_customer_response(self, customer_query: str, context_data: Dict[str, Any]) -> str:
        """Generate automated customer service responses"""
        try:
            prompt = f"""
            Customer Query: "{customer_query}"
            
            Context Data: {json.dumps(context_data, indent=2)}
            
            Please provide a helpful, professional response that:
            1. Addresses the customer's question directly
            2. Uses the provided context appropriately
            3. Offers additional helpful information
            4. Maintains a friendly, professional tone
            5. Includes next steps if applicable
            
            Provide a natural, conversational response (not JSON format).
            """
            
            response = self._make_request(prompt)
            return response if response else "I apologize, but I'm unable to process your request at this time. Please contact our support team for assistance."
                
        except Exception as e:
            logger.error(f"Error generating customer response: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again later or contact support."

# Global instance
gemini_ai_service = GeminiAIService()

def get_gemini_service():
    """Get the global Gemini AI service instance"""
    return gemini_ai_service
