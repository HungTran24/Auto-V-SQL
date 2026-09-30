import sqlite3
import os
import json

def setup_superhero_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Tạo các bảng danh mục (Lookup/Dimension tables)
    cur.execute("""
    CREATE TABLE gender (
        id INTEGER PRIMARY KEY,
        gender TEXT
    );
    """)
    cur.executemany("INSERT INTO gender VALUES (?, ?);", [
        (1, 'Male'), (2, 'Female'), (3, 'Other')
    ])
    
    cur.execute("""
    CREATE TABLE colour (
        id INTEGER PRIMARY KEY,
        colour TEXT
    );
    """)
    cur.executemany("INSERT INTO colour VALUES (?, ?);", [
        (1, 'No Colour'), (2, 'Blue'), (3, 'Brown'), (4, 'Green'), 
        (5, 'Blond'), (6, 'Black'), (7, 'Red'), (8, 'White')
    ])
    
    cur.execute("""
    CREATE TABLE race (
        id INTEGER PRIMARY KEY,
        race TEXT
    );
    """)
    cur.executemany("INSERT INTO race VALUES (?, ?);", [
        (1, 'Human'), (2, 'Mutant'), (3, 'Alien'), (4, 'Cyborg'), (5, 'God / Eternal')
    ])
    
    cur.execute("""
    CREATE TABLE publisher (
        id INTEGER PRIMARY KEY,
        publisher_name TEXT
    );
    """)
    cur.executemany("INSERT INTO publisher VALUES (?, ?);", [
        (1, 'Marvel Comics'), (2, 'DC Comics'), (3, 'Dark Horse Comics'), (4, 'Image Comics')
    ])
    
    cur.execute("""
    CREATE TABLE alignment (
        id INTEGER PRIMARY KEY,
        alignment TEXT
    );
    """)
    cur.executemany("INSERT INTO alignment VALUES (?, ?);", [
        (1, 'Good'), (2, 'Bad'), (3, 'Neutral')
    ])
    
    # 2. Tạo bảng chính: superhero (Nhiều foreign keys)
    cur.execute("""
    CREATE TABLE superhero (
        id INTEGER PRIMARY KEY,
        superhero_name TEXT,
        full_name TEXT,
        gender_id INTEGER,
        eye_colour_id INTEGER,
        hair_colour_id INTEGER,
        skin_colour_id INTEGER,
        race_id INTEGER,
        publisher_id INTEGER,
        alignment_id INTEGER,
        height_cm INTEGER,
        weight_kg INTEGER,
        FOREIGN KEY (gender_id) REFERENCES gender(id),
        FOREIGN KEY (eye_colour_id) REFERENCES colour(id),
        FOREIGN KEY (hair_colour_id) REFERENCES colour(id),
        FOREIGN KEY (skin_colour_id) REFERENCES colour(id),
        FOREIGN KEY (race_id) REFERENCES race(id),
        FOREIGN KEY (publisher_id) REFERENCES publisher(id),
        FOREIGN KEY (alignment_id) REFERENCES alignment(id)
    );
    """)
    
    superheroes = [
        (1, '3-D Man', 'Charles Chandler', 1, 3, 4, 1, 1, 1, 1, 188, 90),
        (2, 'A-Bomb', 'Richard Milhouse Jones', 1, 2, 1, 2, 1, 1, 1, 203, 441),
        (3, 'Abe Sapien', 'Abraham Sapien', 1, 2, 1, 2, 1, 3, 1, 191, 65),
        (4, 'Abin Sur', 'Lagzia', 1, 2, 1, 7, 3, 2, 1, 185, 90),
        (5, 'Abomination', 'Emil Blonsky', 1, 4, 1, 4, 1, 1, 2, 203, 441),
        (6, 'Batgirl', 'Barbara Gordon', 2, 2, 7, 8, 1, 2, 1, 170, 57),
        (7, 'Black Canary', 'Dinah Drake', 2, 2, 5, 8, 1, 2, 1, 165, 58),
        (8, 'Supergirl', 'Kara Zor-El', 2, 2, 5, 8, 3, 2, 1, 171, 54),
        (9, 'Hellboy', 'Anung Un Rama', 1, 7, 6, 7, 3, 3, 1, 211, 180),
        (10, 'Ghost', 'Celeste', 2, 2, 5, 8, 1, 3, 1, 173, 59)
    ]
    cur.executemany("INSERT INTO superhero VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", superheroes)
    
    # 3. Tạo các bảng liên kết thuộc tính và năng lực (N-N relationships)
    cur.execute("""
    CREATE TABLE attribute (
        id INTEGER PRIMARY KEY,
        attribute_name TEXT
    );
    """)
    cur.executemany("INSERT INTO attribute VALUES (?, ?);", [
        (1, 'Intelligence'), (2, 'Strength'), (3, 'Speed'), (4, 'Durability'), (5, 'Power'), (6, 'Combat')
    ])
    
    cur.execute("""
    CREATE TABLE hero_attribute (
        hero_id INTEGER,
        attribute_id INTEGER,
        attribute_value INTEGER,
        PRIMARY KEY (hero_id, attribute_id),
        FOREIGN KEY (hero_id) REFERENCES superhero(id),
        FOREIGN KEY (attribute_id) REFERENCES attribute(id)
    );
    """)
    hero_attributes = [
        (1, 1, 50), (1, 2, 35), (1, 3, 45), (1, 4, 55),
        (2, 2, 100), (2, 4, 90), (3, 1, 88), (3, 2, 30),
        (6, 1, 88), (6, 6, 90), (7, 2, 40), (7, 6, 95),
        (8, 2, 100), (8, 3, 100), (8, 5, 100), (9, 2, 85),
        (10, 1, 75), (10, 3, 80)
    ]
    cur.executemany("INSERT INTO hero_attribute VALUES (?, ?, ?);", hero_attributes)
    
    cur.execute("""
    CREATE TABLE superpower (
        id INTEGER PRIMARY KEY,
        power_name TEXT
    );
    """)
    cur.executemany("INSERT INTO superpower VALUES (?, ?);", [
        (1, 'Flight'), (2, 'Super Strength'), (3, 'Telepathy'), (4, 'Healing'), (5, 'Invisibility')
    ])
    
    cur.execute("""
    CREATE TABLE hero_power (
        hero_id INTEGER,
        power_id INTEGER,
        PRIMARY KEY (hero_id, power_id),
        FOREIGN KEY (hero_id) REFERENCES superhero(id),
        FOREIGN KEY (power_id) REFERENCES superpower(id)
    );
    """)
    cur.executemany("INSERT INTO hero_power VALUES (?, ?);", [
        (1, 2), (2, 2), (3, 3), (4, 1), (6, 3), (7, 4), (8, 1), (8, 2), (9, 2), (9, 4), (10, 5)
    ])
    
    conn.commit()
    conn.close()
    print(f"[OK] Database setup complete at: {db_path}")

def get_test_benchmark():
    """
    Tập test benchmark gồm các câu hỏi từ Simple đến Challenging (theo đúng các case study trong paper).
    """
    return [
        {
            "id": 1,
            "difficulty": "Simple",
            "question": "What is the full name and height in cm of the superhero named 'Abe Sapien'?",
            "gold_sql": "SELECT full_name, height_cm FROM superhero WHERE superhero_name = 'Abe Sapien';"
        },
        {
            "id": 2,
            "difficulty": "Moderate",
            "question": "List the superhero names of all heroes whose publisher is 'Marvel Comics'.",
            "gold_sql": """SELECT superhero.superhero_name 
FROM superhero 
INNER JOIN publisher ON superhero.publisher_id = publisher.id 
WHERE publisher.publisher_name = 'Marvel Comics';"""
        },
        {
            "id": 3,
            "difficulty": "Challenging",
            "question": "Please list the superhero names of all the superheroes that have blue eyes and blond hair.",
            "gold_sql": """SELECT T1.superhero_name 
FROM superhero AS T1 
INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id 
INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id 
WHERE T2.colour = 'Blue' AND T3.colour = 'Blond';"""
        },
        {
            "id": 4,
            "difficulty": "Challenging",
            "question": "List the eyes, hair and skin colour of all female superheroes published by Dark Horse Comics.",
            "gold_sql": """SELECT eye_colour.colour AS eye_colour, hair_colour.colour AS hair_colour, skin_colour.colour AS skin_colour 
FROM superhero 
LEFT JOIN gender ON superhero.gender_id = gender.id 
LEFT JOIN colour AS eye_colour ON superhero.eye_colour_id = eye_colour.id 
LEFT JOIN colour AS hair_colour ON superhero.hair_colour_id = hair_colour.id 
LEFT JOIN colour AS skin_colour ON superhero.skin_colour_id = skin_colour.id 
LEFT JOIN publisher ON superhero.publisher_id = publisher.id 
WHERE gender.gender = 'Female' AND publisher.publisher_name = 'Dark Horse Comics';"""
        },
        {
            "id": 5,
            "difficulty": "Moderate",
            "question": "How many superheroes have 'Good' alignment and are of 'Human' race?",
            "gold_sql": """SELECT COUNT(superhero.id) 
FROM superhero 
INNER JOIN alignment ON superhero.alignment_id = alignment.id 
INNER JOIN race ON superhero.race_id = race.id 
WHERE alignment.alignment = 'Good' AND race.race = 'Human';"""
        },
        {
            "id": 6,
            "difficulty": "Challenging",
            "question": "Find the superhero names that have the attribute 'Strength' with a value greater than or equal to 85.",
            "gold_sql": """SELECT superhero.superhero_name 
FROM superhero 
INNER JOIN hero_attribute ON superhero.id = hero_attribute.hero_id 
INNER JOIN attribute ON hero_attribute.attribute_id = attribute.id 
WHERE attribute.attribute_name = 'Strength' AND hero_attribute.attribute_value >= 85;"""
        }
    ]

if __name__ == "__main__":
    db_file = os.path.abspath("do_an/data/superhero.sqlite")
    setup_superhero_db(db_file)
