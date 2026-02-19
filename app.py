import os
from flask import Flask, render_template, request, redirect, url_for
import pyodbc
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Config
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
DB_SERVER = os.getenv('DB_SERVER')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DRIVER = os.getenv('DB_DRIVER')

def get_db_connection():
    conn_str = f'DRIVER={DB_DRIVER};SERVER={DB_SERVER};PORT=1433;DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD}'
    return pyodbc.connect(conn_str)

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Veritabanından notları çekiyoruz (READ)
    cursor.execute("SELECT Id, Title, Content, ImageUrl, CreatedAt FROM Notes ORDER BY CreatedAt DESC")
    columns = [column[0] for column in cursor.description]
    notes = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return render_template('index.html', notes=notes)

@app.route('/add', methods=['POST'])
def add_note():
    title = request.form.get('title')
    content = request.form.get('content')
    file = request.files.get('image')
    image_url = None

    if file:
        # 1. Resim varsa Azure Storage'a yükle
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container="images", blob=file.filename)
        blob_client.upload_blob(file, overwrite=True)
        image_url = blob_client.url

    # 2. Veritabanına kaydet (CREATE)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Notes (Title, Content, ImageUrl) VALUES (?, ?, ?)", (title, content, image_url))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_note(id):
    # 3. Notu sil (DELETE)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Notes WHERE Id = ?", (id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)