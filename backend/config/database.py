import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self):
        """Connect to MongoDB"""
        try:
            mongodb_uri = os.getenv('MONGODB_URI')
            if not mongodb_uri:
                raise ValueError("MONGODB_URI not found in environment variables")

            self.client = MongoClient(mongodb_uri)
            self.db = self.client.savings_app

            # Test connection
            self.client.admin.command('ping')
            print("✓ Successfully connected to MongoDB!")

            return self.db
        except Exception as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("Database connection closed")

# Global database instance
db_instance = Database()
