import psycopg2

try:
    conn = psycopg2.connect(
        dbname="vneuron_db",
        user="postgres", # or your username
        password="sql123",
        host="localhost",
        port="5432"
    )
    print("Successfully connected to V-NEURON database!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")