import os, random, time, schedule, datetime, threading, traceback, logging, hashlib
from flask import Flask, request, session, redirect, render_template, g
from loc_tools import GameScraper, saltGet, saltPass, chores, confirm_mail, gen_unique_token, token_expiration, wishlist_process, time_get
from flask_seasurf import SeaSurf
from databaseMan import close_db, before_request

## TODO: Update the various functions in loc_tools, including converting to OOP when needed and using email templates whenever possible.

## SETUP ##

app = Flask(__name__, static_url_path='/static')
csrf = SeaSurf()
csrf.init_app(app)
app.secret_key = os.environ['sessionKey']
PATH = "static/html/"
logging.basicConfig(filename='app.log', level=logging.DEBUG)
app.teardown_appcontext(close_db)
app.before_request(before_request)

## Index ##

@app.route("/", methods=["GET"])
def index():
  if session.get('logged_in'):
    return redirect('/game_list')
  base = g.base
  users = base.get_all_users()
  print(f"{len(users)} users in db")
  games = base.get_all_games()
  print(f"{len(games)} games in db")
  for game in games:
    print(game["price"])
  return render_template('index.html', text=request.args.get("t"))

## SIGN UP ##

@csrf.include
@app.route("/signup", methods=["GET"])
def signup():
  if session.get('logged_in'):
    return redirect('/game_list')
  return render_template("signup.html", text=request.args.get("t"))


@app.route("/sign", methods=["POST"])
def sign():
  try:
    form = request.form
    username = form.get("username").lower()
    salt = saltGet()
    password = saltPass(form.get("password"), salt)
    email = form.get("email")
    base = g.base
    matches = base.get_all_users()
    if any(m["username"] == username for m in matches):
      raise Exception("Username already exists!")
    if any(m["email"] == email for m in matches):
      raise Exception("Email already exists!")
    account_creation = datetime.datetime.now().strftime("%m-%d-%Y %I:%M:%S %p")
    base.add_user(username, password, salt, email, account_creation)
    base.update_user(username, "email_confirmed", False)
    base.update_user(username, "last_login", "Never Logged In")
    base.update_user(username, "admin", False)
    confirm_email(username)
    text = f"You are signed up as {username}. Please confirm your email address before logging in!"
    logging.info(f"{text}")
    return redirect(f"/login?t={text}")
  except Exception as e:
    text = "Error! {e}"
    return redirect(f"/signup?t={text}")

## LOGIN ##

@csrf.include
@app.route("/login", methods=["GET"])
def login():
  text = request.args.get("t")
  if session.get('logged_in'):
    return redirect(f'/game_list?={text}')
  recover = "Input your email address below to recover your password."
  return render_template("login.html", text=text, recover=recover)


@app.route("/log", methods=["POST"])
def log_in():
  try:
    form = request.form
    username = form.get("username")
    password = form.get("password")
    base = g.base
    current_time = datetime.datetime.now()
    match = next((m for m in base.get_all_users() if m["username"] == username), None)
    if not match:
      raise Exception("Invalid login!")
    salt = match["salt"]
    password = saltPass(password, salt)
    last_login = current_time.strftime("%m-%d-%Y %I:%M:%S %p")
    if not match["password"] == password:
      raise Exception("Invalid login!")
    if match["email_confirmed"] == False:
      token = next((t for t in base.get_all_tokens() if t["username"] == username and t["token_spent"] == True), None)
      if not token:
        raise Exception("Email not confirmed! Please confirm your email address!")
      confirm_email(username)
      text = "Email Confirmation Sent! Please check your Email."
      return redirect(f"/login?t={text}") 
    if match["admin"] == True:
      base.update_user(username, "last_login", last_login)
      session.update({"username": username, "admin": True, "logged_in": True})
      text = f"{match['username']} (Admin!) Logged In!"
      return redirect(f"/game_list?t={text}")
    else:
      base.update_user(username, "last_login", last_login)
      session.update({"username": username, "logged_in": True})
      text = "User Logged In!"
      logging.info(f"{text}")
      return redirect(f"/game_list?t={text}")
  except Exception as e:
    text = "{e} Error!"
    logging.debug(f"{e}")
    return redirect(f"/login?t={text}")

## EMAIL CONFIRMATION ##

def confirm_email(username) -> None:
  try:
    db_key = gen_unique_token(username)
    base = g.base
    match = next((m for m in base.get_all_tokens() if m["id"] == db_key), None)
    if not match:
      raise Exception("Invalid Token!")
    confirm_mail(match["email"], match["token"], "confirm")
  except Exception as e:
    logging.debug(f"Error! {e}")


@app.route("/confirm", methods=["GET"])
def confirm():
  if session.get("logged_in"):
    text = "You are already logged in!"
    return redirect(f"/game_list?t={text}")
  try:
    token = request.args.get("t")
    type = request.args.get("ty")
    base = g.base
    match = next((m for m in base.get_all_tokens() if m["token"] == token and not m["token_spent"]), None)
    if not match:
      raise Exception("Invalid Token!")
    username = match["username"]
    if not token_expiration(token):
      user = next((u for u in base.get_all_users() if u["username"] == username), None)
      if not user:
        raise Exception("Invalid User!")
      if type == "confirm":
        base.update_user(username, "email_confirmed", True)
        base.update_token(token, "token_spent", True)
        text = "Email Confirmed!"
        return redirect(f"/login?t={text}")
      elif type == "recovery":
        text = "Please update your password!"
        return redirect(f"/pass?t={text}&token={token}")
    else:
        base.update_token(token, "token_spent", True)
        raise Exception("Token Expired!")
  except Exception as e:
    text = f"Error! {e}"
    logging.debug(f"{e}")
    return redirect(f"/login?t={text}")

## PASSWORD RECOVERY ##

@csrf.include
@app.route("/pass_recover", methods=["GET"])
def pass_recover():
  text = request.args.get("t")
  return render_template("recovery.html", text=text)


@app.route("/recover", methods=["POST"])
def email_check():
  form = request.form
  email = form.get("email")
  base = g.base
  try:
    match = next(m for m in base.get_all_users() if m["email"] == email)
    if not match:
      raise Exception("Invalid Email!")
    username = match["username"]
    db_key = gen_unique_token(username)
    tm = next(tm for tm in base.get_all_tokens() if db_key == tm)
    if not tm:
      raise Exception("Invalid Token!")
    token = tm["token"]
    confirm_mail(email, token, "recovery")
    text = "Please check your email to recover password."
    return redirect(f"/login?t={text}")
  except StopIteration as e:
      text = f"Error! {e}"
      logging.debug(f"{e}")
      return redirect(f"/pass_recover?t={text}")  

@csrf.include
@app.route("/pass", methods=["GET"])
def pass_reset_page():
  text = request.args.get("t")
  token = request.args.get("token")
  return render_template("reset.html", text=text, token=token)

@app.route("/password_reset", methods=["POST"])
def pass_reset_funct():
  try:
    form = request.form
    token = form.get("token")
    password = form.get("password")
    base = g.base
    match = next((m for m in base.get_all_tokens() if m["token"] == token), None)
    if not match:
        raise Exception("Invalid Token")
    username = match["username"]
    user = next((u for u in base.get_all_users() if u["username"] == username), None)
    if not user:
        raise Exception("Invalid Username")
    salt = saltGet()
    password = saltPass(password, salt)
    base.update_token(token, "token_spent", True)
    base.update_user(username, "password", password)
    base.update_user(username, "salt", salt)
    text = "Password Reset! Please login."
    return redirect(f"/login?t={text}")
  except Exception as e:
      text = f"Error! {e}"
      logging.debug(f"{e}")
      return redirect(f"/login?t={text}")

## GAME LIST ##

@app.route("/game_list", methods=['GET'])
def game_list():
  if not session.get('logged_in'):
    return redirect("/")
  text = request.args.get("t")
  username = session.get("username")
  base = g.base
  game_list = base.get_games_by_username(username)
  #print(game_list)
  num_of_games = len(game_list)
  return render_template("game_list.html",
                         game_list=game_list,
                         user=username,
                         text=text,
                         admin=session.get("admin", False),
                         num_of_games=num_of_games)


@csrf.exempt
@app.route("/price_add", methods=['POST'])
def price_add():
  if not session.get('logged_in'):
    return redirect("/")
  base = g.base
  try:
    form = request.form
    url = form.get("url")
    username = session.get("username")
    s = GameScraper(url)
    logging.debug(f"[Price Add Function] {s.name} - {s.price} - {s.for_sale} - {s.has_demo} - {s.bundle}")
    target_price = f"${round(float(s.price[1:]) * 0.85, 2):.2f}" if s.for_sale else "$0"
    string_time, _ = time_get()
    if any(m["game_name"] == s.name for m in base.get_games_by_username(username)):
      raise Exception("Game Already Added! Try another URL!")
    base.add_game(s.name,
                  s.price, 
                  url, 
                  username, 
                  s.bundle, 
                  s.imageURL, 
                  s.for_sale, 
                  s.has_demo, 
                  s.discount, 
                  string_time,
                  target_price
    )
    text = f"{s.name} Added!"
    return redirect(f"/game_list?t={text}")
  except Exception as e:
    logging.debug("Error! {e}")
    text = "Something went wrong!"
    return redirect(f"/game_list?t={text}")


@csrf.exempt
@app.route("/price_target", methods=['POST'])
def price_target():
  if not session.get("logged_in"):
    text = "You are not logged in!"
    return redirect(f"/login?t={text}")
  try:
    base = g.base
    form = request.form
    username = session.get("username")
    game = form.get("game")
    target_price = form.get("target")
    if not target_price:
      raise Exception("You must enter a target price!")
    target_price = float(target_price.replace("$", ""))
    match = next((m for m in base.get_all_games() if m["game_name"] == game and m["username"] == username), None)
    if not match:
        raise Exception(f"{game} not found for user {username}!")
    price = float(match["price"].replace("$", ""))
    if target_price > price:
        raise Exception("Target price must be below current price!")
    else:
      target_percent = round((target_price - price) / (price * 100), 2)
      target_price = f"${target_price:.2f}"
      text = f"{game}'s target price is now {target_price}!"
      base.update_game(match["game_name"], "target_percent", target_percent)
      base.update_game(match["game_name"], "target_price", target_price)
      return redirect(f"/game_list?t={text}")
  except Exception as e:
    text = f"Error! {e}"
    return redirect(f"/game_list?t={text}")


@csrf.exempt
@app.route("/wishlist_add", methods=['POST'])
def wishlist_add():
  if not session.get("logged_in"):
    text = "You are not logged in!"
    return redirect(f"/login?t={text}")
  else:
    form = request.form
    username = session.get("username")
    steamID = form.get("steamID")
    job = schedule.every(5).seconds.do(
      lambda: wishlist_add_func(steamID, username, job))
    text = "Processing Wishlist"
    return redirect(f"/game_list?t={text}")


def wishlist_add_func(steamID, username, job):
  try:
    wishlist_process(steamID, username)
    text = "Wishlist added!"
    schedule.cancel_job(job)
    return redirect(f"/game_list?t={text}")
  except Exception as e:
    text = f"Error! {e}"
    schedule.cancel_job(job)
    return redirect(f"/game_list?t={text}")


@app.route("/delete_game", methods=["GET"])
def delete_game():
  if not session.get("logged_in"):
    text = "You are not logged in!"
    return redirect(f"/login?t={text}")
  try:
    base = g.base
    game = request.args.get("d")
    username = session.get("username")
    matches = base.get_games_by_username(username)
    logging.info(game)
    match = next((m for m in matches if m["game_name"] == game))
    if not match:
      raise Exception(f"{game} Not Found!")
    base.delete_game(match["game_name"])
    text = f"{game} Deleted!"
    return redirect(f"/game_list?t={text}")
  except Exception as e:
    text = f"Error! {e}"
    return redirect(f"/game_list?t={text}")


## ADMIN PANEL ##


@csrf.include
@app.route("/admin", methods=['GET'])
def admin_panel():
  if not session.get("admin") and session.get("logged_in"):
    text = "You are not an Admin!"
    return redirect(f"/?t={text}")
  base = g.base
  return render_template("admin.html",
                         user_list=base.get_all_users(),
                         user=session.get("username"),
                         text=request.args.get("t"))


@app.route("/delete", methods=['POST'])
def delete_user():
  if not session.get("admin") and session.get("logged_in"):
    text = "You are not an Admin!"
    return redirect(f"/?t={text}")
  try:
    base = g.base
    form = request.form
    username = form.get("username")
    matches = base.get_all_users()
    if any(m["username"] == username for m in matches):
      match = next(m for m in matches if m["username"] == username)
      if not match:
        raise Exception(f"{username} Not Found!")
      username = match["username"]
      base.delete_user(username)
      text = f"{username} Deleted!"
      return redirect(f"/admin?t={text}")
  except Exception as e:
    text = f"Error! {e}"
    return redirect(f"/admin?t={text}")


@app.route("/chores")
def do_chores():
  if not session.get("logged_in") and session.get("admin"):
    text = "You are not an Admin!"
    return redirect(f"/?t={text}")
  chores()
  text = "Chores Done!"
  return redirect(f"/admin?t={text}")


## LOGOUT ##


@app.route("/logout")
def logout():
  if not session.get('logged_in'):
    text = "Error, not logged in!"
    return redirect(f"/login?t={text}")
  session.clear()
  return redirect("/")


## CHORES/MISC ##


def background_task():
  while True:
    schedule.run_pending()
    time.sleep(5)


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True, port=81)
  #schedule.every(1).hours.do(chores)
  #t = threading.Thread(target=background_task)
  #t.start()
