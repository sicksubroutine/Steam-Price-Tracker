from bs4 import BeautifulSoup
import requests, random, hashlib, string, os, datetime, time, logging
from replit import db
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

PATH = "static/html/"

logging.basicConfig(filename='app.log', level=logging.INFO)

def scrape(url, bundle) -> str:
  try:
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    image = soup.find("link", rel="image_src").get("href")
    image_url = image.split("?t=")[0]
    if bundle:
      #name = <h2 class="pageheader">
      #price = <div class="discount_final_price">
      bundle_name = soup.find("h2", class_="pageheader")
      bundle_price = soup.find("div", class_="discount_final_price")
      for_sale = True
      return bundle_name.text.strip(), bundle_price.text.strip(
      ), image_url, for_sale
    else:
      #game name = <div class="apphub_AppName">
      game_name = soup.find("div", class_="apphub_AppName")
      #game price = <div class="game_purchase_price price">
      game_price = soup.find("div", class_="game_purchase_price price")
      section = soup.find("div", class_="game_purchase_action")
      discount = section.find("div", class_="discount_final_price")
      if discount != None:
        game_price = discount
      elif game_price == None:
        not_for_sale = soup.find("div",
                                 class_="game_area_comingsoon game_area_bubble")
        when = not_for_sale.find_all("span")
        when = when[:-1]
        year = when[1].text
        for_sale = False
        game_price = f"Not for Sale until {year}"
        game_name = game_name.text.strip()
        return game_name, game_price, image_url, for_sale
      if not "$" in game_price.text.strip():
        game_price = soup.find_all("div", class_="game_purchase_price price")
        game_price = game_price[1]
      for_sale = True
      return game_name.text.strip(), game_price.text.strip(), image_url, for_sale
  except:
    logging.info("Error scraping page")
    return "Error", "Error", "Error", "Error"

def purge_old_tokens() -> None:
  try:
    expire_grace = datetime.datetime.now()
    expire_grace = expire_grace + datetime.timedelta(hours=1)
    old_token = expire_grace + datetime.timedelta(hours=4)
    matches = db.prefix("token")
    count = 0
    for match in matches:
      expiry_time = db[match]["token_expiration_time"]
      expiry_time = datetime.datetime.strptime(expiry_time, "%m-%d-%Y %I:%M:%S %p")
      if db[match]["token_spent"] == True:
        if expiry_time > expire_grace:
          del db[match]
          count +=1
          logging.info("Token Purged")
      elif expiry_time > old_token:
        del db[match]
        count +=1
        logging.info("Token Purged")
    logging.info(f"{count} Tokens Purged")
  except:
    logging.info(f"Error purging old tokens")
    pass


def compare() -> None:
  try:
    count = 0
    matches = db.prefix("game")
    for match in matches:
      url = db[match]["url"]
      bundle = db[match]["bundle"]
      if bundle == "Not a Bundle":
        bundle = False
      else:
        bundle = True
      name, new_price, image_url, for_sale = scrape(url, bundle)
      if for_sale and db[match]["for_sale"] == False:
        pass
        logging.info(f"{db[match]['game_name']} is now for sale!")
        #TODO: send mail that game is now for sale
      new_price = float(new_price[1:])
      old_price = float(db[match]["price"][1:])
      percent_change = round((new_price - old_price) / old_price * 100, 2)
      target_percent = float(db[match]["target_percent"])
      if target_percent == None:
        target_percent = float(-15)
      if new_price != old_price:
        count +=1
        if percent_change <= target_percent:
          username = db[match]["username"]
          user_list = db.prefix("user")
          for user in user_list:
            if db[user]["username"] == username:
              email = db[user]["email"]
            else:
              continue
          db[match]["old_price"] = f"${old_price}"
          db[match]["price"] = f"${new_price}"
          db[match]["percent_change"] = f"{percent_change}"
          logging.info(f"{name} - {new_price} - decreased by {percent_change}%")
          price_change_mail(email, old_price, new_price, percent_change, url,
                            name, image_url)
        else:
          db[match]["old_price"] = f"${old_price}"
          db[match]["price"] = f"${new_price}"
          db[match]["percent_change"] = f"{percent_change}"
          logging.info(f"{name} Price increased by {percent_change}%")
      else:
        logging.info(f"{name} Price not changed")
        continue
    logging.info(f"{count} Prices Updated")
  except:
    logging.info("Error updating prices!")
    pass
    
def price_change_mail(recipent, old, new, per, url, name, image_url) -> None:
  with open(f"{PATH}price_change.html", "r") as f:
    template = f.read()
  template = template.replace("{image_url}", image_url)
  template = template.replace("{percent_change}", f"{per}")
  template = template.replace("{desc}", name)
  template = template.replace("{link}", url)
  template = template.replace("{old}", f"{old}")
  template = template.replace("{new}", f"{new}")
  server = os.environ.get("SMTP_SERVER")
  port = 587
  s = smtplib.SMTP(host=server, port=port)
  s.starttls()
  username = os.environ['mailUsername']
  password = os.environ['mailPassword']
  s.login(username, password)
  msg = MIMEMultipart()
  msg['To'] = recipent
  msg['From'] = os.environ['emailFrom']
  msg['Subject'] = "Steam Tracker Price Change!"
  msg.attach(MIMEText(template, 'html'))
  s.send_message(msg)
  logging.info(f"{recipent} has been emailed a price change email.")
  del msg


def confirm_mail(recipent, token, type) -> None:
  URL = "https://scraping-steam-prices.thechaz.repl.co/"
  with open(f"{PATH}confirm_token.html", "r") as f:
      template = f.read()
  if type == "confirm":
      template = template.replace("{token}", token)
      template = template.replace(
        "{desc}", "Confirm your Email Address by clickling below.")
      template = template.replace("{url}", f"{URL}/")
      template = template.replace("{type}", type)
  elif type == "recovery":
      template = template.replace("{token}", token)
      template = template.replace(
        "{desc}", "Recover your password by clicking the link below.")
      template = template.replace("{url}", f"{URL}/")
      template = template.replace("{type}", type)
  else:
    logging.info(f"{type} is not a valid option")
    return
  server = os.environ.get("SMTP_SERVER")
  port = 587
  s = smtplib.SMTP(host=server, port=port)
  s.starttls()
  username = os.environ['mailUsername']
  password = os.environ['mailPassword']
  s.login(username, password)
  msg = MIMEMultipart()
  msg['To'] = recipent
  msg['From'] = os.environ['emailFrom']
  msg['Subject'] = "Confirmation Email"
  msg.attach(MIMEText(template, 'html'))
  s.send_message(msg)
  logging.info(f"{recipent} has been emailed a confirmation email.")
  del msg


def saltPass(pwd, salt) -> str:
  pwd = (pwd + str(salt)).encode('utf-8')
  return hashlib.sha256(pwd).hexdigest()


def saltGet() -> str:
  return ''.join(
    random.choice(string.ascii_letters + string.digits + string.punctuation)
    for _ in range(30))


def tokenGet() -> str:
  return ''.join(
    random.choice(string.ascii_letters + string.digits) for _ in range(30))


def gen_unique_token(username) -> str:
  token = tokenGet().lower()
  # create a token creation time
  current_time_date = datetime.datetime.now()
  # set expiration for 30 minutes
  token_expiration_time = current_time_date + datetime.timedelta(minutes=30)
  token_expiration_time = token_expiration_time.strftime(
    "%m-%d-%Y %I:%M:%S %p")
  logging.info(token_expiration_time)
  matches = db.prefix("user")
  for match in matches:
    if db[match]["username"] == username:
      email = db[match]["email"]
  db_key = f"token{time.time()}"
  db[db_key] = {
    "token": token,
    "token_request_date": current_time_date.strftime("%m-%d-%Y %I:%M:%S %p"),
    "token_expiration_time": token_expiration_time,
    "username": username,
    "email": email,
    "token_spent": False
  }
  return db_key

def token_expiration(token) -> bool:
  now = datetime.datetime.now()
  matches = db.prefix("token")
  for match in matches:
    if db[match]["token"] == token and db[match]["token_spent"] == False:
      expiry_time = db[match]["token_expiration_time"]
      expiry_time = datetime.datetime.strptime(expiry_time, "%m-%d-%Y %I:%M:%S %p")
      if now > expiry_time:
        return True
      elif now < expiry_time:
        return False

def time_get() -> str:
  time = datetime.datetime.now()
  PT_time = time - datetime.timedelta(hours=8)
  string_time = PT_time.strftime("%m-%d-%Y %I:%M:%S %p")
  return string_time, PT_time

def chores() -> None:
  try:
    now_str, now = time_get()
    logging.info(f"Chores starting at {now_str}")
    purge_old_tokens()
    compare()
    after_str, after = time_get()
    time_taken = after - now
    # convert to seconds
    time_taken = round(time_taken.total_seconds(), 2)
    logging.info(f"Chores finished at {after_str}")
    logging.info(f"Time taken: {time_taken} Seconds")
    logging.info("====CHORES=RUN=COMPLETE====")
  except:
    logging.info("====CHORES=RUN=FAILED====")
    pass