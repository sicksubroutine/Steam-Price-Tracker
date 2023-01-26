import os, random
from replit import db
from flask import Flask, request, session, redirect
from loc_tools import scrape, saltGet, saltPass

#libs not used yet
#from email.mime.multipart import MIMEMultipart
#from email.mime.text import MIMEText
#import smtplib, time, schedule

app = Flask(__name__, static_url_path='/static')

app.secret_key = os.environ['sessionKey']

PATH = "static/html/"

@app.route("/")
def index():
  if session.get('logged_in'):
    return redirect('/game_list')
  with open(f"{PATH}index.html", "r") as f:
    return f.read()

@app.route("/signup", methods=["GET"])
def signup():
  with open(f"{PATH}signup.html", "r") as f:
    page = f.read()
  text = request.args.get("t")
  if text == None:
    page = page.replace("{t}", "")
    return page
  page = page.replace("{t}", text)
  return page

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
  
@app.route("/login", methods=["GET"])
def login():
  text = request.args.get("t")
  with open(f"{PATH}login.html", "r") as f:
    page = f.read()
  if text == None:
    page = page.replace("{t}", "")
    return page
  page = page.replace("{t}", text)
  return page

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
      text = "Invalid Username or Password!"
      return redirect(f"/login?t={text}")
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

@app.route("/price_add", methods=['POST'])
def price_add():
  if session.get('logged_in'):
    pass
  else:
    return redirect("/")
  form = request.form
  url = form.get("url")
  bundle = form.get("bundle")
  if bundle == None:
    bundle = False
    name, price = scrape(url, bundle)
  else:
    bundle = True
    name, price = scrape(url, bundle)
  matches = db.prefix("game")
  for match in matches:
    if db[match]["game_name"] == None:
      continue
    elif db[match]["game_name"] == name:
      text = "Game Already Added! Try another URL!"
      return redirect(f"/game_list?t={text}")
  game_key = "game" + str(random.randint(100_000_000, 999_999_999))
  db[game_key] = {"game_name": name, "price": price, "url": url, "username": session.get("username"), "bundle": bundle}
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

@app.route("/logout")
def logout():
  if session.get('logged_in'):
    session.pop("username", None)
    session.pop("logged_in", None)
    session.pop("admin", None)
    return redirect("/")
  else:
    return "Error, not logged in!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81)
