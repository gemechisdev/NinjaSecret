# MongoDB Database Integration

This directory contains MongoDB database operations and models for the bot.

## Structure

The MongoDB integration follows a simple pattern:

### Database Connection
```python
from NinjaSecret.utils.mongo import db

# Create a collection
collection_name = db.your_collection
```

### Basic Operations

#### Create/Update Document
```python
async def save_data(user_id: int, data: dict):
    await collection_name.update_one(
        {"user_id": user_id}, 
        {"$set": data}, 
        upsert=True
    )
```

#### Find Document
```python
async def get_data(user_id: int):
    user = await collection_name.find_one({"user_id": user_id})
    return user if user else None
```

#### Delete Document
```python
async def remove_data(user_id: int):
    await collection_name.delete_one({"user_id": user_id})
```

#### Get All Documents
```python
async def get_all_data():
    cursor = collection_name.find({"user_id": {"$gt": 0}})
    return [doc async for doc in cursor]
```

## Example Files

- `afkdb.py` - Example AFK (Away From Keyboard) database operations
- `readable_time.py` - Utility for time formatting

## Creating New Database Models

1. Create a new Python file in this directory
2. Import the database connection: `from NinjaSecret.utils.mongo import db`
3. Define your collection: `your_collection = db.collection_name`
4. Implement CRUD operations following the patterns above

## Best Practices

- Always use async/await for database operations
- Use upsert=True for update operations when you want to create if not exists
- Handle exceptions appropriately
- Use meaningful collection and field names
- Index frequently queried fields for better performance

## Configuration

Make sure your MongoDB URI is properly configured in your environment variables:
```
MONGO_DB_URI=mongodb+srv://username:password@cluster.mongodb.net/database_name
```