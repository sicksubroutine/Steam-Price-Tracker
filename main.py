import os, random, time, schedule, datetime, threading, traceback, logging, pickle
from replit import db
from flask import Flask, request, session, redirect, render_template
from loc_tools import scrape, saltGet, saltPass, chores, confirm_mail, gen_unique_token, token_expiration, wishlist_process, time_get
from flask_seasurf import SeaSurf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

## TODO: Ability to import Steam Wishlist
## TODO: Take into account "free games" being in a wishlist
## TODO: Take into account games in a "pre-order" state
## TODO: Make game list not look ugly on mobile screen sizes
## TODO: Make bundle checking function actually work (ie, not just scanning for "Bundle")


## SETUP ##

app = Flask(__name__, static_url_path='/static')
csrf = SeaSurf()
csrf.init_app(app)
app.secret_key = os.environ['sessionKey']
PATH = "static/html/"
logging.basicConfig(filename='app.log', level=logging.INFO)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

## Testing/Direct Database Modification ##

"""
count = 0
#game testing area
matches = db.prefix("game")
print(f"{len(matches)} games in DB")
for match in matches:
  if db[match]["wishlist"]:
    del db[match]
print(f"{count} games detected")


#user testing area
matches = db.prefix("user")
for match in matches:
  if db[match]["username"] == "test_account":
    db[match]["last_login"] = "Not yet Logged in"

#token testing area
count = 0
matches = db.prefix("token")
for match in matches:
  del db[match]
  count += 1
print(f"{count}")
"""

## Index ##

@app.route("/", methods=["GET"])
def index():
  if session.get('logged_in'):
    return redirect('/game_list')
  return render_template('index.html', text=request.args.get("t"))


## SIGN UP ##


@csrf.include
@app.route("/signup", methods=["GET"])
def signup():
  if session.get('logged_in'):
    return redirect('/game_list')
  return render_template("signup.html", text=request.args.get("t"))


@app.route("/sign", methods=["POST"])
@limiter.limit("3 per hour")
def sign():
  try:
    form = request.form
    username = form.get("username").lower()
    salt = saltGet()
    password = saltPass(form.get("password"), salt)
    email = form.get("email")
    matches = db.prefix("user")
    for match in matches:
      if db[match]["username"] == username:
        text = "Username already taken!"
        return redirect(f"/signup?t={text}")
      if db[match]["email"] == email:
        text = "Email already exists!"
        return redirect(f"/signup?t={text}")
    user_num = "user" + str(random.randint(100_000_000, 999_999_999))
    account_creation = datetime.datetime.now()
    account_creation = account_creation.strftime("%m-%d-%Y %I:%M:%S %p")
    db[user_num] = {
      "username": username,
      "password": password,
      "salt": salt,
      "email": email,
      "admin": False,
      "creation_date": account_creation,
      "email_confirmed": False,
      "last_login": "Never Logged In",
    }
    confirm_email(username)
    text = f"You are signed up as {username}. Please confirm your email address before logging in!"
    logging.info(f"{text}")
    return redirect(f"/login?t={text}")
  except:
    text = "Something went wrong!"
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
@limiter.limit("25 per hour")
def log_in():
  try:
    form = request.form
    username = form.get("username")
    password = form.get("password")
    matches = db.prefix("user")
    for match in matches:
      if db[match]["username"] == username:
        current_time = datetime.datetime.now()
        salt = db[match]["salt"]
        password = saltPass(password, salt)
        if db[match]["username"] == username and db[match][
            "password"] == password and db[match]["admin"] == True:
          db[match]["last_login"] = current_time.strftime(
            "%m-%d-%Y %I:%M:%S %p")
          session["username"] = username
          session["admin"] = True
          session["logged_in"] = True
          text = f"{db[match]['username']} (Admin!) Logged In!"
          return redirect(f"/game_list?t={text}")
        elif db[match]["username"] == username and db[match][
            "password"] == password:
          if db[match]["email_confirmed"] == False:
            # check if user has a confirmation token
            tokens = db.prefix("token")
            for token in tokens:
              if db[token]["username"] == username and db[token][
                  "token_spent"] == True:
                # create new token and send email
                confirm_email(username)
                text = "Email Confirmation Sent! Please check your Email."
                return redirect(f"/login?t={text}")
              elif db[token]["username"] == username and db[token][
                  "token_spent"] == False:
                text = "Email not confirmed! Please confirm your email address!"
                return redirect(f"/login?t={text}")
            else:
              # if no tokens are found, prompt user to confirm email
              confirm_email(username)
              text = "Email Confirmation Sent! Please check your Email."
              return redirect(f"/login?t={text}")
          db[match]["last_login"] = current_time.strftime(
            "%m-%d-%Y %I:%M:%S %p")
          session["username"] = username
          session["logged_in"] = True
          text = f"{username} Logged In!"
          logging.info(f"{text}")
          return redirect(f"/game_list?t={text}")
    text = "Invalid login"
    return redirect(f"/login?t={text}")
  except:
    text = "Invalid login! Something went wrong."
    return redirect(f"/login?t={text}")


## EMAIL CONFIRMATION ##


def confirm_email(username) -> None:
  db_key = gen_unique_token(username)
  matches = db.prefix("token")
  for match in matches:
    if db_key == match:
      confirm_mail(db[match]["email"], db[match]["token"], "confirm")


@app.route("/confirm", methods=["GET"])
def confirm():
  if session.get("logged_in"):
    text = "You are already logged in!"
    return redirect(f"/game_list?t={text}")
  try:
    token = request.args.get("t")
    type = request.args.get("ty")
    users = db.prefix("user")
    matches = db.prefix("token")
    for match in matches:
      if token == db[match]["token"] and db[match]["token_spent"] == False:
        username = db[match]["username"]
        if token_expiration(token) == False:
          for user in users:
            if db[user]["username"] == username:
              if type == "confirm":
                db[match]["token_spent"] = True
                db[user]["email_confirmed"] = True
                text = "Email Confirmed!"
                return redirect(f"/login?t={text}")
              elif type == "recovery":
                text = "Please update your password!"
                return redirect(f"/pass?t={text}&token={token}")
        elif token_expiration(token):
          db[match]["token_spent"] = True
          text = "Token Expired!"
          return redirect(f"/login?t={text}")
    else:
      text = "Error! Invalid Token!"
      return redirect(f"/login?t={text}")
  except:
    text = "Something went wrong!"
    return redirect(f"/login?t={text}")


## PASSWORD RECOVERY ##


@csrf.include
@app.route("/pass_recover", methods=["GET"])
def pass_recover():
  text = request.args.get("t")
  return render_template("recovery.html", text=text)


@app.route("/recover", methods=["POST"])
@limiter.limit("5 per hour")
def email_check():
  try:
    form = request.form
    email = form.get("email")
    matches = db.prefix("user")
    for match in matches:
      if db[match]["email"] == email:
        username = db[match]["username"]
        db_key = gen_unique_token(username)
        token_match = db.prefix("token")
        for tm in token_match:
          if db_key == tm:
            token = db[tm]["token"]
            confirm_mail(email, token, "recovery")
            text = "Please check your email to recover password."
            return redirect(f"/login?t={text}")
    else:
      text = "Error! Invalid Email!"
      return redirect(f"/pass_recover?t={text}")
  except:
    text = "Something went wrong!"
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
    matches = db.prefix("token")
    users = db.prefix("user")
    for match in matches:
      if token == db[match]["token"]:
        username = db[match]["username"]
        for user in users:
          if db[user]["username"] == username:
            salt = saltGet()
            password = saltPass(form.get("password"), salt)
            db[match]["token_spent"] = True
            db[user]["password"] = password
            db[user]["salt"] = salt
            text = "Password Reset! Please login."
            return redirect(f"/login?t={text}")
        else:
          text = "Error! Invalid Username!"
          return redirect(f"/login?t={text}")
    else:
      text = "Error! Invalid Token!"
      return redirect(f"/login?t={text}")
  except:
    text = "Something went wrong!"
    return redirect(f"/login?t={text}")

## GAME LIST ##

@app.route("/game_list", methods=['GET'])
def game_list():
  if not session.get('logged_in'):
    return redirect("/")
  now = datetime.datetime.now()
  username = session.get("username")
  text = request.args.get("t")
  matches = db.prefix("game")
  db_games_for_user = [db[match] for match in matches if db[match]["username"] == username]
  games_user_has = len(db_games_for_user)
  logging.info(f"{games_user_has} games for {username}")
  if os.path.exists(f'.game-list/{username}_picked_list.pickle'):
    with open(f'.game-list/{username}_picked_list.pickle', 'rb') as f:
      game_list = pickle.load(f)
      logging.info("Loaded game list from pickle")
      game_list_len = len(game_list)
    if game_list_len != games_user_has:
      game_list = game_list_func(username)
      with open(f'.game-list/{username}_picked_list.pickle', 'wb') as f:
        pickle.dump(game_list, f)
        logging.info("Saved game list to pickle")
    #logging.info("# of games updated, loaded game list from function.")
  else:
    game_list = game_list_func(username)
    with open(f'.game-list/{username}_picked_list.pickle', 'wb') as f:
      pickle.dump(game_list, f)
      logging.info("Saved game list to pickle")
  admin = False
  game_list_len = len(game_list)
  logging.info(f"{game_list_len} games in list")
  if session.get("admin"):
    admin = True
  after = datetime.datetime.now()
  logging.info(f"{after - now} seconds elapsed")
  return render_template("game_list.html",
                         game_list=game_list,
                    user=session.get("username"),
                         text=text, admin=admin)  

def game_list_func(username):
  game_list = []
  matches = db.prefix("game")
  matches_filter = [match for match in matches if db[match]["username"] == username]
  game_list = [{
        "url": db[match]["url"],
        "old_price": db[match]["old_price"],
        "image_url": db[match]["image_url"],
        "game_name": db[match]["game_name"],
        "game_price": db[match]['price'],
        "percent_change": db[match]["percent_change"],
        "bundle": db[match]["bundle"],
        "target_price": db[match]["target_price"],
        "has_demo": db[match]["has_demo"],
        "price_change_date": db[match]["price_change_date"],
        "for_sale": db[match]["for_sale"]
    } for match in matches_filter]
  return game_list


@csrf.exempt
@app.route("/price_add", methods=['POST'])
def price_add():
  if not session.get('logged_in'):
    return redirect("/")
  try:
    form = request.form
    url = form.get("url")
    username = session.get("username")
    name, price, image_url, for_sale, has_demo, bundle = scrape(url)
    logging.info(f"[Price Add Function] {name} - {price} - {for_sale} - {has_demo} - {bundle}")
    if for_sale:
      price_t = price
      price_t = float(price_t[1:])
      target_price = round(price_t - (price_t * 0.15), 2)
      target_price = f"${target_price:.2f}"
    else:
      target_price = "$0"
    string_time, PT_time = time_get()
    matches = db.prefix("game")
    for match in matches:
      if db[match]["game_name"] == name:
        text = "Game Already Added! Try another URL!"
        return redirect(f"/game_list?t={text}")
    game_key = "game" + str(random.randint(100_000_000, 999_999_999))
    db[game_key] = {
      "game_name": name,
      "price": price,
      "url": url,
      "username": username,
      "bundle": bundle,
      "image_url": image_url,
      "old_price": "$0",
      "percent_change": "0",
      "for_sale": for_sale,
      "target_percent": "-10",
      "target_price": target_price,
      "price_change_date": "",
      "wishlist": False,
      "has_demo": has_demo,
      "date_added": string_time
    }
    text = f"{name} Added!"
    return redirect(f"/game_list?t={text}")
  except:
    logging.info(traceback.format_exc())
    text = "Something went wrong!"
    return redirect(f"/game_list?t={text}")

@csrf.exempt
@app.route("/price_target", methods=['POST'])
def price_target():
  if not session.get("logged_in"):
    text = "You are not logged in!"
    return redirect(f"/login?t={text}")
  try:
    form = request.form
    username = session.get("username")
    game = form.get("game")
    target_price = form.get("target")
    if "$" in target_price:
      target_price = target_price.replace("$", "")
    if target_price == "":
      text = "You must enter a target price!"
      return redirect(f"/game_list?t={text}")
    else:
      matches = db.prefix("game")
      for match in matches:
        if db[match]["game_name"] == game and db[match]["username"] == username:
          price = db[match]["price"]
          price = float(price.replace("$", ""))
          target_price = float(target_price)
          if target_price > price:
            text = f"{game}'s target price needs to be below ${price}!"
            return redirect(f"/game_list?t={text}")
          else:
            target_percent = round((target_price - price) / (price * 100), 2)
            target_price = f"${target_price:.2f}"
            text = f"{game}'s target price is now {target_price}!"
            db[match]["target_percent"] = f"{target_percent}"
            db[match]["target_price"] = f"{target_price}"
            return redirect(f"/game_list?t={text}")
    return f"{target_price} for {game}"
  except:
    text = "Something went wrong!"
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
    job = schedule.every(5).seconds.do(lambda: wishlist_add_func(steamID, username, job))
    text = "Processing Wishlist"
    return redirect(f"/game_list?t={text}")

def wishlist_add_func(steamID, username, job):
  try:
    wishlist_process(steamID, username)
    text = "Wishlist added!"
    schedule.cancel_job(job)
    return redirect(f"/game_list?t={text}")
  except:
    text = "Something went wrong!"
    schedule.cancel_job(job)
    return redirect(f"/game_list?t={text}")
    

@app.route("/delete_game", methods=["GET"])
def delete_game():
  if not session.get("logged_in"):
    text = "You are not logged in!"
    return redirect(f"/login?t={text}")
  try:
    game = request.args.get("d")
    user = session.get("username")
    matches = db.prefix("game")
    logging.info(game)
    for match in matches:
      if db[match]["game_name"] == game and db[match]["username"] == user:
        del db[match]
        text = f"{game} Deleted!"
        return redirect(f"/game_list?t={text}")
    text = f"{game} Not Found!"
    return redirect(f"/game_list?t={text}")
  except:
    text = "Something went wrong!"
    return redirect(f"/game_list?t={text}")


## ADMIN PANEL ##


@csrf.include
@app.route("/admin", methods=['GET'])
def admin_panel():
  if not session.get("admin") and session.get("logged_in"):
    text = "You are not an Admin!"
    return redirect(f"/?t={text}")
  user_list = []
  matches = db.prefix("user")
  for match in matches:
    user_list.append({
      "username": db[match]["username"],
      "email": db[match]["email"],
      "admin": db[match]["admin"],
      "last_login": db[match]["last_login"],
      "creation_date": db[match]["creation_date"],
      "email_confirmed": str(db[match]["email_confirmed"])
    })
  text = request.args.get("t")
  return render_template("admin.html",
                         user_list=user_list,
                         user=session.get("username"),
                         text=text)
    


@app.route("/delete", methods=['POST'])
def delete_user():
  if not session.get("admin") and session.get("logged_in"):
    text = "You are not an Admin!"
    return redirect(f"/?t={text}")
  try:
    form = request.form
    username = form.get("username")
    matches = db.prefix("user")
    for match in matches:
      if db[match]["username"] == username:
        username = db[match]["username"]
        del db[match]
        text = f"{username} Deleted!"
        return redirect(f"/admin?t={text}")
  except:
    text = "Something went wrong!"
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
  session.pop("username", None)
  session.pop("logged_in", None)
  session.pop("admin", None)
  return redirect("/")

## CHORES/MISC ##

def background_task():
  while True:
    schedule.run_pending()
    time.sleep(5)

if __name__ == "__main__":
  schedule.every(6).hours.do(chores)
  t = threading.Thread(target=background_task)
  t.start()
  app.run(host='0.0.0.0', port=81)
