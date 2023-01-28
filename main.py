import os, random, time, schedule, datetime
from replit import db
from flask import Flask, request, session, redirect, render_template
from loc_tools import scrape, saltGet, saltPass, compare
from flask_seasurf import SeaSurf

#TODO: Create differet "sections" on the game list (bundles, games not for sale, and so on)
#TODO: Implement password reset
#TODO: Implement rate limiting on password requests/account creation
#TODO: Recovery Token Expiration System
#TODO: Add error handling (try, except)
#TODO: Add Email Confirmation
#TODO: Convert as many routes to render_template as possible
#TODO: Add price change date

app = Flask(__name__, static_url_path='/static')
csrf = SeaSurf()
csrf.init_app(app)
app.secret_key = os.environ['sessionKey']
PATH = "static/html/"

"""#game testing area
matches = db.prefix("game")
for match in matches:
  if db[match]["for_sale"] == "True":
    if db[match]["game_name"] == "Rain World":
      print(db[match])"""

"""
#user testing area
matches = db.prefix("user")
for match in matches:
  db[match]["email_confirmed"] = "True"
"""


@app.route("/", methods=["GET"])
def index():
  if session.get('logged_in'):
    return redirect('/game_list')
  return render_template('index.html', text=request.args.get("t"))


@csrf.include
@app.route("/signup", methods=["GET"])
def signup():
  if session.get('logged_in'):
    return redirect('/game_list')
  return render_template("signup.html", text=request.args.get("t"))


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
  account_creation = datetime.datetime.now()
  account_creation = account_creation.strftime("%m-%d-%Y %I:%M:%S %p")
  db[user_num] = {
    "username": username,
    "password": password,
    "salt": salt,
    "email": email,
    "admin": False,
    "creation_date": account_creation,
    "email_confirmed": "False"
  }
  text = f"You are signed up as {username}. Please Login!"
  return redirect(f"/login?t={text}")


@csrf.include
@app.route("/login", methods=["GET"])
def login():
  text = request.args.get("t")
  if session.get('logged_in'):
    return redirect(f'/game_list?={text}')
  text = request.args.get("t")
  return render_template("login.html", text=text)


@app.route("/log", methods=["POST"])
def log():
  form = request.form
  username = form.get("username")
  password = form.get("password")
  matches = db.prefix("user")
  for match in matches:
    current_time = datetime.datetime.now()
    if db[match]["username"] == username:
      salt = db[match]["salt"]
      password = saltPass(password, salt)
    else:
      continue
    if db[match]["username"] == username and db[match][
        "password"] == password and db[match]["admin"] == True:
      db[match]["last_login"] = current_time.strftime("%m-%d-%Y %I:%M:%S %p")
      session["username"] = username
      session["admin"] = True
      session["logged_in"] = True
      text = f"{db[match]['username']} (Admin!) Logged In!"
      return redirect(f"/game_list?t={text}")
    elif db[match]["username"] == username and db[match][
        "password"] == password:
      db[match]["last_login"] = current_time.strftime("%m-%d-%Y %I:%M:%S %p")
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
  username = session.get("username")
  if bundle == None:
    bundle = False
    name, price, image_url, for_sale = scrape(url, bundle)
    bundle = "Not a Bundle"
  else:
    bundle = True
    name, price, image_url, for_sale = scrape(url, bundle)
    bundle = "Bundle"
  price_t = price
  price_t = float(price_t[1:])
  target_price = round(price_t - (price_t * 0.15), 2)
  target_price = f"${target_price:.2f}"
  current_time = datetime.datetime.now()
  matches = db.prefix("game")
  for match in matches:
    if db[match]["game_name"] == None:
      continue
    elif db[match]["game_name"] == name:
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
    "date_added": current_time.strftime("%m-%d-%Y %I:%M:%S %p")
  }
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
      l = l.replace("{url}", db[match]["url"])
      l = l.replace("{image_url}", db[match]["image_url"])
      l = l.replace("{old}", db[match]["old_price"])
      l = l.replace("{game_name}", db[match]["game_name"])
      l = l.replace("{game_price}", db[match]['price'])
      l = l.replace("{percent_change}", db[match]["percent_change"])
      l = l.replace("{bundle}", db[match]["bundle"])
      l = l.replace("{target_price}", db[match]["target_price"])
      result += l
    else:
      continue
  if session.get("admin"):
    page = page.replace(
      "{admin}",
      "<a href='/admin'><button class ='btn' id='back'>Admin</button></a>")
  else:
    page = page.replace("{admin}", "")
  page = page.replace("{game_list}", result)
  username = session.get("username")
  page = page.replace("{user}", username)
  if text == None:
    page = page.replace("{t}", "")
  else:
    page = page.replace("{t}", text)
  return page


@csrf.include
@app.route("/admin", methods=['GET'])
def admin():
  if session.get("admin") and session.get("logged_in"):
    user_list = []
    matches = db.prefix("user")
    for match in matches:
      user_list.append({
        "username": db[match]["username"],
        "email": db[match]["email"],
        "admin": db[match]["admin"],
        "last_login": db[match]["last_login"],
        "creation_date": db[match]["creation_date"]
      })
    text = request.args.get("t")
    return render_template("admin.html",
                           user_list=user_list,
                           user=session.get("username"),
                           text=text)
  else:
    text = "You are not an Admin!"
    return redirect(f"/login?t={text}")


@app.route("/delete", methods=['POST'])
def delete():
  if session.get("admin") and session.get("logged_in"):
    form = request.form
    username = form.get("username")
    matches = db.prefix("user")
    for match in matches:
      if db[match]["username"] == username:
        username = db[match]["username"]
        del db[match]
        text = f"{username} Deleted!"
        return redirect(f"/admin?t={text}")
  else:
    text = "You are not an Admin!"
    return redirect(f"/?t={text}")


@csrf.exempt
@app.route("/price_target", methods=['POST'])
def price_target():
  if session.get("logged_in"):
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
            text = f"{game}'s target price is now ${target_price}!"
            target_percent = round((target_price - price) / (price * 100), 2)
            db[match]["target_percent"] = f"{target_percent}"
            db[match]["target_price"] = f"${target_price}"
            return redirect(f"/game_list?t={text}")
    return f"{target_price} for {game}"
  else:
    text = "You are not logged in!"
    return redirect(f"/login?t={text}")


@app.route("/delete_game", methods=["GET"])
def delete_game():
  if session.get("logged_in"):
    game = request.args.get("d")
    user = session.get("username")
    matches = db.prefix("game")
    print(game)
    for match in matches:
      if db[match]["game_name"] == game and db[match]["username"] == user:
          del db[match]
          text = f"{game} Deleted!"
          return redirect(f"/game_list?t={text}")
    text = f"{game} Not Found!"
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


#compare()
schedule.every().day.at("18:00").do(compare)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=81)
  while True:
    schedule.run_pending()
    time.sleep(5)
