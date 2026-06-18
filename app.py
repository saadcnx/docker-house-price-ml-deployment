import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import joblib
import os

class HousePricePredictor:
    def __init__(self):
        self.model = LinearRegression()
        self.is_trained = False
    
    def generate_sample_data(self, n_samples=1000):
        """Generate sample house data for training"""
        np.random.seed(42)
        
        # Generate features: size, bedrooms, age
        size = np.random.normal(2000, 500, n_samples)
        bedrooms = np.random.randint(1, 6, n_samples)
        age = np.random.randint(0, 50, n_samples)
        
        # Generate price based on features with some noise
        price = (size * 100 + bedrooms * 5000 - age * 1000 + 
                np.random.normal(0, 10000, n_samples))
        
        # Ensure positive prices
        price = np.maximum(price, 50000)
        
        data = pd.DataFrame({
            'size': size,
            'bedrooms': bedrooms,
            'age': age,
            'price': price
        })
        
        return data
    
    def train_model(self):
        """Train the model with sample data"""
        print("Generating training data...")
        data = self.generate_sample_data()
        
        X = data[['size', 'bedrooms', 'age']]
        y = data['price']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        print("Training model...")
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        print(f"Model trained successfully. MSE: {mse:.2f}")
        
        self.is_trained = True
        
        # Save the model
        joblib.dump(self.model, 'house_price_model.pkl')
        print("Model saved as house_price_model.pkl")
    
    def load_model(self):
        """Load a pre-trained model"""
        if os.path.exists('house_price_model.pkl'):
            self.model = joblib.load('house_price_model.pkl')
            self.is_trained = True
            print("Model loaded successfully")
        else:
            print("No saved model found. Training new model...")
            self.train_model()
    
    def predict(self, size, bedrooms, age):
        """Make a prediction"""
        if not self.is_trained:
            self.load_model()
        
        features = np.array([[size, bedrooms, age]])
        prediction = self.model.predict(features)[0]
        return max(prediction, 0)  # Ensure non-negative price

if __name__ == "__main__":
    predictor = HousePricePredictor()
    predictor.train_model()
