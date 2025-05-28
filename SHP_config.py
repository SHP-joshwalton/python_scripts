from dotenv import load_dotenv
import os

# Specify the path to the .env file
dotenv_path = os.path.join('/var/www', '.env')
load_dotenv(dotenv_path)

if __name__ == '__main__':
    print(os.getenv('SERVER_ENVIRONMENT'))
    pass