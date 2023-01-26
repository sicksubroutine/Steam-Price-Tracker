import os, random, time, schedule
from replit import db
from flask import Flask, request, session, redirect, render_template
from loc_tools import scrape, saltGet, saltPass, compare
from flask_seasurf import SeaSurf

#TODO: Ability to set percent change target
#TODO: Ability to set game price target
#TODO: Account for games that aren't for sale
#TODO: Implement password reset
#TODO: Implement rate limiting on password requests/account creation
#TODO: Recovery Token Expiration System
#TODO: Admin panel to do maintence on users
#TODO: Add error handling (try, except)
#TODO: Add Email Confirmation

app = Flask(__name__, static_url_path='/static')
csrf = SeaSurf()
csrf.init_app(app)
app.secret_key = os.environ['sessionKey']
PATH = "static/html/"

#testing area
matches = db.prefix("game")
for match in matches:
  if db[match]["game_name"] == "HYPER DEMON":
    
    db[match]["old_price"] = "$0"
    db[match]["percent_change"] = "0"
  #print(f"{db[match]}")

@app.route("/", methods=["GET"])
def index():
  if session.get('logged_in'):
    return redirect('/game_list')
  text = request.args.get("t")
  return render_template('index.html', text=text)

@csrf.include
@app.route("/signup", methods=["GET"])
def signup():
  text = request.args.get("t")
  return render_template("signup.html", text=text)
  
@app.route("/sign", methods=["POST"])
def sign():
  form = request.form 
  username = form.get("username")
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
  db[user_num] = {"username": username, "password": password, "salt": salt, "email": email, "admin": False}
  text = f"You are signed up as {username}. Please Login!"
  return redirect(f"/login?t={text}")

@csrf.include
@app.route("/login", methods=["GET"])
def login():
  text = request.args.get("t")
  return render_template("login.html", text=text)

@app.route("/log", methods=["POST"])
def log():
  form = request.form 
  username = form.get("username")
  password = form.get("password")
  matches = db.prefix("user")
  for match in matches:
    if db[match]["username"] == username:
      salt = db[match]["salt"]
      password = saltPass(password, salt)
    else:
      continue
    if db[match]["username"] == username and db[match]["password"] == password and db[match]["admin"] == True:
      session["username"] = username
      session["admin"] = True
      session["logged_in"] = True
      text = f"{db[match]['username']} (Admin!) Logged In!"
      return redirect(f"/game_list?t={text}")
    elif db[match]["username"] == username and db[match]["password"] == password:
      session["username"] = username
      session["logged_in"] = True
      text = f"{username} Logged In!"
      return redirect(f"/game_list?t={text}")
    else:
      text = "Invalid Username or Password!"
      return redirect(f"/login?t={text}")

"""@app.route("/recover", methods=["GET"])
def recover_password():
  pass"""
@csrf.exempt
@app.route("/price_add", methods=['POST'])
def price_add():
  if session.get('logged_in'):
    pass
  else:
    return redirect("/")
  form = request.form
  url = form.get("url")
  bundle = form.get("bundle")
  print(bundle)
  username = session.get("username")
  if bundle == None:
    bundle = False
    name, price, image_url = scrape(url, bundle)
    bundle = "Not a Bundle"
  else:
    bundle = True
    name, price, image_url = scrape(url, bundle)
    bundle = "Bundle"
  matches = db.prefix("game")
  for match in matches:
    if db[match]["game_name"] == None:
      continue
    elif db[match]["game_name"] == name:
      text = "Game Already Added! Try another URL!"
      return redirect(f"/game_list?t={text}")
  game_key = "game" + str(random.randint(100_000_000, 999_999_999))
  db[game_key] = {"game_name": name, "price": price, "url": url, "username": username, "bundle": bundle, "image_url": image_url}
  text = f"{name} Added!"
  return redirect(f"/game_list?t={text}")

@app.route("/game_list", methods=['GET'])
def game_list():
  if session.get('logged_in'):
    pass
  else:
    return redirect("/")
  text = request.args.get("t")
  result = ""
  with open(f"{PATH}game_item.html", "r") as f:
    list = f.read()
  with open(f"{PATH}game_list.html", "r") as f:
    page = f.read()
  matches = db.prefix("game")
  for match in matches:
    if session.get("username") == db[match]["username"]:
      l = list
      l = l.replace("{game_name}", db[match]["game_name"])
      l = l.replace("{game_price}", db[match]["price"])
      l = l.replace("{old_price}", "")
      l = l.replace("{percent_change}", "<span class='red'>25% Decrease</span>")
      l = l.replace("{bundle}", db[match]["bundle"])
      result += l
    else:
      continue
  page = page.replace("{game_list}", result)
  username = session.get("username")
  page = page.replace("{user}", username)
  if text == None:
    page = page.replace("{t}", "")
  else:
    page = page.replace("{t}", text)
  return page

@app.route("/admin")
def admin():
  if session.get("logged_in"):
    if session.get("admin"):
      pass
    else:
      text = "You are not an Admin!"
      return redirect(f"/game_list?t={text}")
  else:
    text = "You are not logged in!"
    return redirect(f"/login?t={text}")

@app.route("/logout")
def logout():
  if session.get('logged_in'):
    session.pop("username", None)
    session.pop("logged_in", None)
    session.pop("admin", None)
    return redirect("/")
  else:
    text = "Error, not logged in!"
    return redirect(f"/login?t={text}")

schedule.every().day.at("18:00").do(compare)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=81)
  while True:
    schedule.run_pending()
    time.sleep(5)