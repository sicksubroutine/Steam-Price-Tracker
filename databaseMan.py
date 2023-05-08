import random, time, sqlite3
from flask import g
DATABASE = "prime_database.db"

class DatabaseManager:

  def __init__(self, open_db):
    self.open_db = open_db
    self.users_table = "users"
    self.games_table = "games"
    self.tokens_table = "tokens"
    self.setup_database()

  def setup_database(self):
    self.conn = self.open_db()
    schema = '''
      CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY,
          username TEXT UNIQUE,
          password TEXT,
          salt TEXT,
          email TEXT UNIQUE,
          admin BOOLEAN,
          creation_date TEXT,
          email_confirmed BOOLEAN,
          last_login TEXT
      );

      CREATE TABLE IF NOT EXISTS games (
          id TEXT PRIMARY KEY,
          game_name TEXT NOT NULL,
          price REAL NOT NULL,
          url TEXT NOT NULL,
          username TEXT NOT NULL,
          bundle BOOLEAN NOT NULL DEFAULT FALSE,
          image_url TEXT NOT NULL,
          old_price TEXT NOT NULL,
          percent_change TEXT NOT NULL,
          for_sale BOOLEAN NOT NULL DEFAULT FALSE,
          target_percent INTEGER NOT NULL DEFAULT -10,
          target_price REAL NOT NULL,
          price_change_date TEXT,
          wishlist BOOLEAN NOT NULL DEFAULT FALSE,
          has_demo BOOLEAN NOT NULL DEFAULT FALSE,
          discount TEXT,
          date_added TEXT NOT NULL,
          FOREIGN KEY (username) REFERENCES users (username)
      );

      CREATE TABLE IF NOT EXISTS tokens (
          id TEXT PRIMARY KEY,
          token TEXT NOT NULL,
          token_request_date TEXT NOT NULL,
          token_expiration_time TEXT NOT NULL,
          username TEXT NOT NULL,
          email TEXT NOT NULL,
          token_spent INTEGER NOT NULL DEFAULT 0
      );
      '''
    self.conn.executescript(schema)
    self.conn.commit()
    
  def add_user(self, username, password, salt, email, account_creation):
    user_key = f"user{random.randint(100_000_000, 999_999_999)}"
    cursor = self.conn.cursor()
    cursor.execute(
      '''INSERT INTO users
                        (id, username, password, salt, email, creation_date)
                        VALUES (?, ?, ?, ?, ?, ?)''',
      (user_key, username, password, salt, email, account_creation))
    self.conn.commit()
    return user_key

  def update_user(self, username, field, value):
    cursor = self.conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE username = ?",
                   (value, username))
    self.conn.commit()

  def get_user(self, user_id):
    cursor = self.conn.cursor()
    cursor.execute('''SELECT * FROM users WHERE id=?''', (user_id, ))
    user_data = cursor.fetchone()
    return user_data

  def get_user_by_username(self, username):
    cursor = self.conn.cursor()
    cursor.execute('''SELECT * FROM users WHERE username=?''', (username, ))
    return cursor.fetchone()

  def get_all_users(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

  def delete_user(self, username):
    cursor = self.conn.cursor()
    cursor.execute('''DELETE FROM users WHERE username=?''', (username, ))
    self.conn.commit()

  def authenticate_user(self, username, password):
    cursor = self.conn.cursor()
    cursor.execute(
      '''SELECT id FROM users
                        WHERE username=? AND password=?''',
      (username, password))
    user_id = cursor.fetchone()
    return user_id[0] if user_id else None

  def add_game(self, name, price, url, username, bundle, image_url, for_sale,
               has_demo, discount, string_time, target_price):
    game_key = "game" + str(random.randint(100_000_000, 999_999_999))
    cursor = self.conn.cursor()
    cursor.execute(
      '''INSERT INTO games
                        (id, game_name, price, url, username, bundle, image_url, old_price, percent_change,
                         for_sale, target_percent, target_price, price_change_date, wishlist, has_demo,
                         discount, date_added)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
      (game_key, name, price, url, username, bundle, image_url, "$0", "0",
       for_sale, -10, target_price, "", 0, has_demo, discount, string_time))
    self.conn.commit()
    return game_key

  def get_game(self, game_id):
    cursor = self.conn.cursor()
    cursor.execute(f'''SELECT * FROM {self.games_table} WHERE id=?''',
                   (game_id, ))
    game_data = cursor.fetchone()
    return game_data

  def get_games_by_username(self, username):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM games WHERE username = ?", (username,))
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

  def get_all_games(self):
    cursor = self.conn.cursor()
    cursor.execute(f'''SELECT * FROM {self.games_table}''')
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

  def update_game(self, game_name, field, value):
    cursor = self.conn.cursor()
    cursor.execute(f'''UPDATE {self.games_table} SET {field}=? WHERE game_name=?''',
                   (value, game_name))
    self.conn.commit()

  def delete_game(self, game_name):
    cursor = self.conn.cursor()
    cursor.execute(f'''DELETE FROM {self.games_table} WHERE game_name=?''',(game_name, ))
    self.conn.commit()

  def add_token(self, token, token_request_date, token_expiration_time,
                username, email):
    token_key = "token" + str(time.time())
    cursor = self.conn.cursor()
    cursor.execute(
      '''INSERT INTO tokens
                        (id, token, token_request_date, token_expiration_time, username, email)
                        VALUES (?, ?, ?, ?, ?, ?)''',
      (token_key, token, token_request_date, token_expiration_time, username,
       email))
    self.conn.commit()
    return token_key

  def update_token(self, token, field, value):
    cursor = self.conn.cursor()
    cursor.execute(f'''UPDATE {self.tokens_table} SET {field}=? WHERE token=?''',
                   (value, token))
    self.conn.commit()

  def delete_token(self, token):
    cursor = self.conn.cursor()
    cursor.execute(f'''DELETE FROM {self.tokens_table} WHERE token=?''',
                   (token, ))
    self.conn.commit()

  def get_token(self, token_id):
    cursor = self.conn.cursor()
    cursor.execute('''SELECT * FROM tokens WHERE id=?''', (token_id, ))
    token_data = cursor.fetchone()
    return token_data

  def get_all_tokens(self):
    cursor = self.conn.cursor()
    cursor.execute('''SELECT * FROM tokens''')
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

def open_db():
  if 'database' not in g:
    g.database = sqlite3.connect(DATABASE)
    g.database.row_factory = sqlite3.Row
  return g.database

def close_db(error):
  if 'database' in g:
    g.database.close()

def before_request():
  g.base = DatabaseManager(open_db)

  