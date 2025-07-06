#!/usr/bin/env python3
"""
seed.py - MySQL Database Setup with Python Generators

A robust database seeding utility with:
- Environment-based configuration
- Connection pooling
- Comprehensive error handling
- Data validation
- Batch processing
- Context managers for resource handling
"""

import csv
import logging
import os
import uuid
from contextlib import contextmanager
from typing import Iterator, Dict, Any, List, Tuple, Union, Optional

import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_setup.log')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration with environment variables and defaults"""
    HOST = os.getenv('DB_HOST', 'localhost')
    USER = os.getenv('DB_USER', 'root')
    PASSWORD = os.getenv('DB_PASSWORD', '')
    DATABASE = os.getenv('DB_NAME', 'ALX_prodev')
    PORT = int(os.getenv('DB_PORT', 3306))
    POOL_NAME = 'prodev_pool'
    POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 5))


class DatabaseManager:
    """Manage database connections with connection pooling"""
    
    _connection_pool = None

    @classmethod
    def initialize_pool(cls):
        """Initialize the connection pool"""
        if not cls._connection_pool:
            try:
                cls._connection_pool = pooling.MySQLConnectionPool(
                    pool_name=DatabaseConfig.POOL_NAME,
                    pool_size=DatabaseConfig.POOL_SIZE,
                    host=DatabaseConfig.HOST,
                    user=DatabaseConfig.USER,
                    password=DatabaseConfig.PASSWORD,
                    database=DatabaseConfig.DATABASE,
                    port=DatabaseConfig.PORT,
                    autocommit=True
                )
                logger.info("Database connection pool initialized")
            except Error as e:
                logger.error(f"Error initializing connection pool: {e}")
                raise

    @classmethod
    @contextmanager
    def get_connection(cls) -> Iterator[mysql.connector.MySQLConnection]:
        """Get a connection from the pool with context management"""
        if not cls._connection_pool:
            cls.initialize_pool()

        connection = None
        try:
            connection = cls._connection_pool.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Error getting database connection: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()


def create_database() -> bool:
    """Create the database if it doesn't exist"""
    try:
        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES LIKE %s", (DatabaseConfig.DATABASE,))
            
            if cursor.fetchone():
                logger.info(f"Database {DatabaseConfig.DATABASE} already exists")
                return True
                
            cursor.execute(
                f"CREATE DATABASE {DatabaseConfig.DATABASE} "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            logger.info(f"Database {DatabaseConfig.DATABASE} created successfully")
            return True
            
    except Error as e:
        logger.error(f"Error creating database: {e}")
        return False


def create_table() -> bool:
    """Create the user_data table if it doesn't exist"""
    try:
        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = 'user_data'
            """, (DatabaseConfig.DATABASE,))
            
            if cursor.fetchone()[0] > 0:
                logger.info("Table user_data already exists")
                return True
                
            create_table_query = """
            CREATE TABLE user_data (
                user_id CHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                age TINYINT UNSIGNED NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_age (age),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_query)
            logger.info("Table user_data created successfully")
            return True
            
    except Error as e:
        logger.error(f"Error creating table: {e}")
        return False


def validate_user_data(row: Dict[str, Any]) -> bool:
    """Validate user data before insertion"""
    try:
        if not isinstance(row.get('name'), str) or not row['name'].strip():
            return False
            
        if not isinstance(row.get('email'), str) or '@' not in row['email']:
            return False
            
        age = int(row.get('age', 0))
        if not (0 < age <= 120):  # Reasonable age range
            return False
            
        return True
    except (ValueError, TypeError):
        return False


def process_row(row: Dict[str, Any]) -> Tuple[str, str, str, int]:
    """Process and validate a row of user data"""
    row['user_id'] = row.get('user_id') or str(uuid.uuid4())
    row['name'] = str(row.get('name', '')).strip()
    row['email'] = str(row.get('email', '')).strip().lower()
    row['age'] = int(float(row.get('age', 0)))
    
    if not validate_user_data(row):
        raise ValueError(f"Invalid user data: {row}")
        
    return (row['user_id'], row['name'], row['email'], row['age'])


def csv_reader_generator(file_path: str) -> Iterator[Dict[str, Any]]:
    """Generate user data from CSV file with validation"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                try:
                    yield process_row(row)
                except ValueError as e:
                    logger.warning(f"Skipping invalid row: {e}")
    except FileNotFoundError:
        logger.error(f"CSV file not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise


def insert_data(data: Union[str, List[Dict[str, Any]]], batch_size: int = 1000) -> int:
    """
    Insert or update data in the user_data table
    
    Args:
        data: Either a CSV file path or a list of dictionaries
        batch_size: Number of records to insert per batch
        
    Returns:
        int: Number of successfully inserted records
    """
    insert_query = """
    INSERT INTO user_data (user_id, name, email, age)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        email = VALUES(email),
        age = VALUES(age)
    """
    
    total_inserted = 0
    
    try:
        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Handle CSV file input
            if isinstance(data, str):
                if not os.path.exists(data):
                    logger.info(f"CSV file {data} not found. Creating sample data...")
                    create_sample_csv(data)
                data = csv_reader_generator(data)
            
            # Handle list of dictionaries
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                data = (process_row(row) for row in data)
            
            # Batch processing
            batch = []
            for record in data:
                batch.append(record)
                if len(batch) >= batch_size:
                    cursor.executemany(insert_query, batch)
                    total_inserted += len(batch)
                    batch = []
                    logger.debug(f"Inserted {total_inserted} records so far...")
            
            # Insert remaining records
            if batch:
                cursor.executemany(insert_query, batch)
                total_inserted += len(batch)
            
            logger.info(f"Successfully inserted/updated {total_inserted} records")
            return total_inserted
            
    except Error as e:
        logger.error(f"Error inserting data: {e}")
        return 0


def create_sample_csv(file_path: str = "user_data.csv", num_records: int = 1000):
    """Generate sample CSV file with random user data"""
    import random
    from faker import Faker
    
    fake = Faker()
    
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['user_id', 'name', 'email', 'age'])
        
        for _ in range(num_records):
            user_id = str(uuid.uuid4())
            name = fake.name()
            email = fake.email()
            age = random.randint(18, 80)
            writer.writerow([user_id, name, email, age])
    
    logger.info(f"Created sample CSV with {num_records} records at {file_path}")


def stream_all_users(batch_size: int = 1000) -> Iterator[Dict[str, Any]]:
    """Stream all users from the database in batches"""
    query = "SELECT * FROM user_data ORDER BY created_at DESC"
    
    try:
        with DatabaseManager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                for row in rows:
                    yield row
    except Error as e:
        logger.error(f"Error streaming users: {e}")
        raise


def main():
    """Main execution function"""
    try:
        logger.info("Starting database setup...")
        
        # Initialize database
        create_database()
        create_table()
        
        # Seed data
        inserted = insert_data("user_data.csv")
        logger.info(f"Total records processed: {inserted}")
        
        # Example of streaming users
        for i, user in enumerate(stream_all_users()):
            if i == 0:
                logger.info(f"First user: {user}")
                
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise
    finally:
        logger.info("Database setup completed")


if __name__ == "__main__":
    main()
