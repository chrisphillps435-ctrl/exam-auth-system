import mysql.connector

# Connect to database
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="mysql",
    database="exam_authentication"
)
cursor = conn.cursor()

# Ask for login credentials
username = input("Username: ")
password = input("Password: ")

# Check credentials
cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
result = cursor.fetchone()

if result:
    print("Login successful! Welcome admin.")
else:
    print("Login failed. Invalid username or password.")
