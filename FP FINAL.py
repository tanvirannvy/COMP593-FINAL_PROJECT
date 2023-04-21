import requests
import sys
import os
import hashlib
import sqlite3
import re
from datetime import datetime
import shutil

def main():
    # Get command line argument 
    if len(sys.argv) == 2:
        input_date = sys.argv[1]

        # Validate command line argument
        # Validate date format
        date_test = re.compile("\d{4}-\d{2}-\d{2}$")
        if not date_test.match(input_date):
            print("Invalid date format")
            sys.exit()
        # Validate date range
        APOD_start_date = datetime(1995, 6, 16)
        today_date = datetime.today()
        date = datetime.strptime(input_date, '%Y-%m-%d')
        if date <= APOD_start_date or date > today_date:
            print("Date should be between 1995-06-16 and today's date")
            sys.exit()
    else:
        # If no command line argument, use today's date
        today_date = datetime.today()
        input_date = today_date.strftime("%Y-%m-%d")

    # Check if image cache directory exists
    image_cache_dir_name = 'APOD_image_cache'
    image_cache_dir_path = os.path.join(
        os.getcwd(), image_cache_dir_name)

    if not os.path.exists(image_cache_dir_path):
        # Create image cache directory
        os.mkdir(image_cache_dir_path)
        print("Created image cache directory: {}".format(
            image_cache_dir_path))

    # Check if APOD database exists
    db_name = 'NASA_APOD.db'
    db_path = os.path.join(image_cache_dir_path, db_name)

    if not os.path.exists(db_path):
        # Create APOD database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE apod_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            explanation TEXT,
            image_file TEXT,
            hash TEXT
            )
        """)
        conn.commit()
        conn.close()

        print("Created APOD database: {}".format(db_path))

    print('Selected APOD date: {}'.format(input_date))

    # Get APOD information from NASA API
    API_key = 'THIeV6uBy92F1KX1Y6TrxUoTcIQJszgnJAEuG8CH'
    URL = 'https://api.nasa.gov/planetary/apod?api_key={}&date={}'.format(
        API_key, input_date)
    response = requests.get(URL)
    if response.status_code == 200:
        data = response.json()
        title = data['title']
        explanation = data['explanation']
        media_type = data['media_type']
        if media_type == 'image':
            image_file_url = data['hdurl']
        elif media_type == 'video':
            image_file_url = data['thumbnail_url']
        else:
            print('Not a valid APOD media type')

        print('Getting the APOD information from the NASA API')
        print('APOD title: {}'.format(title))
        print('URL of the APOD image file: {}'.format(image_file_url))

        # Download APOD image file
        response_img = requests.get(image_file_url, stream=True)
        image_file_name = re.sub('[^a-zA-Z0-9_]', '',
                                 title).strip().replace(' ', '_') + '.' + image_file_url.split('.')[-1]
        image_file_path = os.path.join(image_cache_dir_path, image_file_name)

        with open(image_file_path, 'wb') as f:
            print('Downloading APOD image')
            response_img.raw.decode_content = True
            shutil.copyfileobj(response_img.raw, f)
        del response_img

        # Generate SHA-256 hashvalue
        sha256 = hashlib.sha256()
        with open(image_file_path, 'rb') as f:
            sha256.update(f.read())
        sha256_hash = sha256.hexdigest()
        print('SHA-256 hash value of the APOD image: {}'.format(
            sha256_hash))

        # Check if APOD image already exists in the cache
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM apod_images WHERE hash LIKE ?",
                  (sha256_hash,))
        record_count = c.fetchone()[0]

        if record_count > 0:
            print('The image already exists in the cache')
        else:
            # Save the APOD image to the cache
            print('Saving the APOD image to the cache')
            print('Full path of the APOD image file saved to the cache: {}'.format(
                image_file_path))

            # Add the image to the database
            c.execute("INSERT INTO apod_images (title, explanation, image_file, hash) VALUES (?, ?, ?, ?)",
                      (title, explanation, image_file_path, sha256_hash))
            conn.commit()
            conn.close()

            print('Adding the image to the database')
    
    else:
        print('Error: Could not get the APOD information from the NASA API')
        sys.exit()

    # Set the desktop background image
    os.system('osascript -e \'tell application "Finder" to set desktop picture to POSIX file "{}"\''.format(image_file_path))
    print('Setting the desktop background image')

if __name__ == "__main__":
    main()