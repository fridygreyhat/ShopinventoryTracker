// Firebase Gemini AI Integration
import { initializeApp } from "firebase/app";
import { getAI, getGenerativeModel, GoogleAIBackend } from "firebase/ai";

// Firebase configuration - replace with your actual values
const firebaseConfig = {
  apiKey: "AIzaSyBc8dD1OwzxWJrf-bAxowOtYj-OHZr2epo",
  authDomain: "inventory-management-75a65.firebaseapp.com",
  projectId: "inventory-management-75a65",
  storageBucket: "inventory-management-75a65.appspot.com",
  messagingSenderId: "your-messaging-sender-id",
  appId: "your-app-id"
};

// Initialize Firebase App
const firebaseApp = initializeApp(firebaseConfig);

// Initialize the Gemini Developer API backend service
const ai = getAI(firebaseApp, { backend: new GoogleAIBackend() });

// Create a GenerativeModel instance with Gemini 2.5 Flash
const model = getGenerativeModel(ai, { model: "gemini-2.5-flash" });

// Gemini AI Service Class
class GeminiAIService {
  constructor() {
    this.model = model;
    this.isInitialized = true;
  }

  // Generate inventory insights
  async generateInventoryInsights(inventoryData) {
    try {
      const prompt = `
        Analyze the following inventory data and provide insights:
        ${JSON.stringify(inventoryData, null, 2)}
        
        Please provide:
        1. Stock level analysis
        2. Reorder recommendations
        3. Trend analysis
        4. Cost optimization suggestions
        5. Risk assessment
        
        Format the response as a structured JSON object.
      `;

      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error('Error generating inventory insights:', error);
      throw error;
    }
  }

  // Generate sales forecasting
  async generateSalesForecasting(salesData) {
    try {
      const prompt = `
        Based on the following sales data, provide sales forecasting:
        ${JSON.stringify(salesData, null, 2)}
        
        Please analyze:
        1. Sales trends
        2. Seasonal patterns
        3. Future sales predictions
        4. Growth opportunities
        5. Performance metrics
        
        Provide actionable recommendations in JSON format.
      `;

      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error('Error generating sales forecast:', error);
      throw error;
    }
  }

  // Generate product recommendations
  async generateProductRecommendations(customerData, inventoryData) {
    try {
      const prompt = `
        Based on customer data and inventory, suggest product recommendations:
        
        Customer Data: ${JSON.stringify(customerData, null, 2)}
        Inventory Data: ${JSON.stringify(inventoryData, null, 2)}
        
        Please provide:
        1. Personalized product recommendations
        2. Cross-selling opportunities
        3. Up-selling suggestions
        4. Seasonal recommendations
        5. Inventory turnover optimization
        
        Format as JSON with product IDs and reasons.
      `;

      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error('Error generating product recommendations:', error);
      throw error;
    }
  }

  // Generate business insights
  async generateBusinessInsights(businessData) {
    try {
      const prompt = `
        Analyze the following business data and provide strategic insights:
        ${JSON.stringify(businessData, null, 2)}
        
        Please provide:
        1. Business performance analysis
        2. Market opportunities
        3. Operational efficiency recommendations
        4. Financial insights
        5. Strategic recommendations
        
        Format as a comprehensive business report in JSON.
      `;

      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error('Error generating business insights:', error);
      throw error;
    }
  }

  // Generate automated responses for customer queries
  async generateCustomerResponse(customerQuery, contextData) {
    try {
      const prompt = `
        Customer Query: "${customerQuery}"
        
        Context Data: ${JSON.stringify(contextData, null, 2)}
        
        Please provide a helpful, professional response that:
        1. Addresses the customer's question
        2. Uses the provided context
        3. Offers additional helpful information
        4. Maintains a friendly, professional tone
        5. Includes next steps if applicable
        
        Format as a customer service response.
      `;

      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error('Error generating customer response:', error);
      throw error;
    }
  }

  // Generate inventory optimization suggestions
  async generateInventoryOptimization(inventoryData, salesData) {
    try {
      const prompt = `
        Optimize inventory based on the following data:
        
        Inventory: ${JSON.stringify(inventoryData, null, 2)}
        Sales Data: ${JSON.stringify(salesData, null, 2)}
        
        Please provide:
        1. Optimal stock levels
        2. Reorder points
        3. Safety stock recommendations
        4. Slow-moving item identification
        5. Cost reduction opportunities
        
        Format as actionable recommendations in JSON.
      `;

      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error('Error generating inventory optimization:', error);
      throw error;
    }
  }
}

// Create global instance
const geminiAI = new GeminiAIService();

// Export for use in other modules
window.GeminiAI = geminiAI;

// Usage examples and helper functions
window.GeminiHelpers = {
  // Helper to safely parse JSON responses
  parseAIResponse: (response) => {
    try {
      // Try to extract JSON from response
      const jsonMatch = response.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[1]);
      }
      
      // Try to parse as direct JSON
      return JSON.parse(response);
    } catch (error) {
      console.warn('Could not parse AI response as JSON:', error);
      return { rawResponse: response };
    }
  },

  // Helper to format AI responses for display
  formatResponse: (response) => {
    const parsed = window.GeminiHelpers.parseAIResponse(response);
    if (parsed.rawResponse) {
      return parsed.rawResponse;
    }
    return JSON.stringify(parsed, null, 2);
  }
};

console.log('✅ Firebase Gemini AI service initialized');
