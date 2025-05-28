from __future__ import annotations
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import SHP_config
import os

class MetaDataUpdater:
    def __init__(self):
        """Initialize database connection."""
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                database=os.getenv('DATABASE_NAME'),
                user=os.getenv('DATABASE_USER_NAME'),
                password=os.getenv('DATABASE_USER_PASSWORD')
            )
            self.cursor = self.connection.cursor()
        except Error as e:
            self.connection = None

    def set_meta_data_for_key(self, meta_key, meta_value):
        self.upsert_meta_data(meta_key, meta_value)
        
    def get_meta_data_for_key(self, meta_key):
        """Fetch meta data for a given key."""
        if not self.connection:
            return None

        try:
            query = "SELECT meta_value FROM meta_data WHERE meta_key = %s"
            self.cursor.execute(query, (meta_key,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Error as e:
            return None
    def upsert_meta_data(self, meta_key, meta_value, created_date=None, updated_date=None):
        """Insert a new record if meta_key does not exist, otherwise update it."""
        if not self.connection:
            return False

        try:
            # Check if the meta_key exists
            check_query = "SELECT COUNT(*) FROM meta_data WHERE meta_key = %s"
            self.cursor.execute(check_query, (meta_key,))
            (count,) = self.cursor.fetchone()

            if count > 0:
                # Update existing meta_key
                query = """
                    UPDATE meta_data
                    SET meta_value = %s
                    WHERE meta_key = %s
                """
                values = (meta_value, meta_key)
                self.cursor.execute(query, values)
            else:
                # Insert new meta_key
                query = """
                    INSERT INTO meta_data (meta_key, meta_value)
                    VALUES (%s, %s)
                """
                values = (meta_key, meta_value)
                self.cursor.execute(query, values)

            # Commit changes
            self.connection.commit()
            return True

        except Error as e:
            return False
    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            self.cursor.close()
            self.connection.close()

# Example Usage:
if __name__ == "__main__":
    updater = MetaDataUpdater()
    updater.upsert_meta_data("last_jira_ticket_pulled", "IT-6153")
    updater.close_connection()
