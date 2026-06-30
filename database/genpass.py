from cassandra.cluster import Cluster
import csv
from werkzeug.security import generate_password_hash
import uuid

users = [
    {'name': 'Joe Rogan', 'user_id': 'fe878ccf-aba7-4b16-8b5f-847f7db6e0ad'},
    {'name': 'Neil deGrasse Tyson', 'user_id': '39eab94a-b6f7-40e1-81d7-9be14b7c867d'},
    {'name': 'Quentin Tarantino', 'user_id': '98806cda-663d-4b4c-8d72-7a1d28ed4f58'},
    {'name': 'Jordan Peterson', 'user_id': '45d4a39e-a9a3-4c27-955a-6d056324c6fd'},
    {'name': 'Jeff Bezos', 'user_id': '6c1b8973-5ebd-4407-8817-02945bcfa561'},
    {'name': 'J.K. Rowling', 'user_id': '8bdce8ab-41e9-49db-a3f5-5cbacd5f60d0'},
    {'name': 'Jeff Goldblum', 'user_id': 'c58998de-48a9-4f9a-9e7a-2ec430fe6e09'},
    {'name': 'David Attenborough', 'user_id': 'aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358'},
    {'name': 'Emma Watson', 'user_id': 'ff52c318-95e0-4f1f-89cc-62551c814a83'},
    {'name': 'Steve Wozniak', 'user_id': '16f033ca-2b2c-4745-a537-82999209774c'},
    {'name': 'Stephen Hawking', 'user_id': '7d6e67f2-5c64-4175-8330-a0d1b2b9c45f'},
    {'name': 'Elon Musk', 'user_id': 'b4dfd93d-a9e0-4bf8-8685-735dbde17ff7'},
    {'name': 'James Cameron', 'user_id': 'a0a79e14-2ea9-4924-a992-6d5e1d7ad0ab'},
    {'name': 'Pope Francis', 'user_id': '1be6b6df-d5f3-4d82-9e15-c3a8c78607dd'},
    {'name': 'Bill Gates', 'user_id': '86eb2b6c-1771-4533-9bd8-fca4f83fe61a'},
    {'name': 'Marie Kondo', 'user_id': '9c89c702-6c61-49c8-9f0c-47b8e4e84e4b'},
    {'name': 'Richard Branson', 'user_id': '2d10e93b-163f-40f0-9b77-1de15e2b5d0c'},
    {'name': 'Barack Obama', 'user_id': '642932c8-63fe-4f06-91c9-0e7e6d8b0756'},
    {'name': 'Morgan Freeman', 'user_id': '84a8f453-80f4-408f-b692-01bfcfeb7b10'},
    {'name': 'Oprah Winfrey', 'user_id': '20bb3797-b82c-4a7b-b3e5-c726ce2a19cd'}
]

# Generate hashed passwords
for user in users:
    first_name = user['name'].split()[0]
    user['password'] = generate_password_hash(first_name)

# Save user details to CSV
csv_file_path = './user_passwords.csv'
with open(csv_file_path, 'w', newline='') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=users[0].keys())
    writer.writeheader()
    writer.writerows(users)

# Connect to Cassandra
cluster = Cluster(['172.18.0.2'])  # Replace with your Cassandra host
cassandra_session = cluster.connect('logosphere')



# Upsert user data into Cassandra
with open('./user_passwords.csv', 'r') as data:
    reader = csv.DictReader(data)
    for row in reader:
        cassandra_session.execute(
            """
            INSERT INTO user_credentials (user_id, email, password)
            VALUES (%s, %s, %s)
            """,
            (uuid.UUID(row['user_id']), row['name'], row['password'])
        )
