# db_connection.py
import os
import SHP_config
import mysql.connector
from mysql.connector import Error

def create_connection():

    try:
        connection = mysql.connector.connect(
            host='localhost',
            database=os.getenv('DATABASE_NAME'),
            user=os.getenv('DATABASE_USER_NAME'),
            password=os.getenv('DATABASE_USER_PASSWORD')
        )

        if connection.is_connected():
            return connection

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def close_connection(connection):
    if connection.is_connected():
        connection.close()

def show_tables(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("Tables in the database:")
        for table in tables:
            print(table[0])
            show_columns(connection= connection, table_name= table[0])
    except Error as e:
        print(f"Error fetching tables: {e}")
    finally:
        cursor.close()

def show_columns(connection, table_name):
    try:
        cursor = connection.cursor()
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        columns = cursor.fetchall()
        print(f"Columns in the table '{table_name}':")
        for column in columns:
            print(column[0])
    except Error as e:
        print(f"Error fetching columns: {e}")
    finally:
        cursor.close()

def show_users(connection, table_name):
    try:
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Error as e:
        print(f"Error fetching columns: {e}")
    finally:
        cursor.close()

def main():
    connection = create_connection()
    if connection is not None:
        show_users(connection, "users")
        connection.close()
    else:
        print("Connection is not established")

if __name__ == "__main__":
    main()
