from bs4 import BeautifulSoup
import requests, random, hashlib, string, os, datetime, time, logging, traceback
from replit import db
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

PATH = "static/html/"
logging.basicConfig(filename='app.log', level=logging.INFO)


def scrape(url):
  try:
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    image = soup.find("link", rel="image_src").get("href")
    bundle_name = soup.find("h2", class_="pageheader")
    bundle_find = soup.find("div", class_="game_area_purchase_game bundle ds_no_flags")
    pre_purchase = pre_purchase_check(soup)
    if bundle_find == None:
      logging.info("No bundle found.")
      bundle = False
    else:
      logging.info("Bundle found.")
      bundle = True
    image_url = image.split("?t=")[0]
    # bundle section
    if bundle:
      bundle_name, bundle_price, for_sale = bundle_scrape(url)
      logging.info(f"=={bundle_name}==")
      return bundle_name, bundle_price, image_url, for_sale, False, True
    else:
      #game name = <div class="apphub_AppName">
      game_name = soup.find("div", class_="apphub_AppName")
      logging.info(f"=={game_name.text.strip()}==")
      game_price = soup.find_all("div", class_="game_purchase_price price")
      logging.debug(f"{game_price}")
      # discount check
      discount = discount_check(soup)
      demo = soup.find("div", class_="game_area_purchase_game demo_above_purchase")
      if discount:
        logging.info("Discount found")
        game_price = discount_price(soup)
      elif not discount:
        logging.info("No Discount")
        #game price = <div class="game_purchase_price price">
        game_price = soup.find("div", class_="game_purchase_price price")
        logging.debug(f"{game_price}")
      if demo == None:
        logging.info("==Has No Demo==")
        has_demo = False
      else:
        has_demo = True
        logging.info("==Has Demo==")
      # not for sale check
      if game_price == None or pre_purchase:
        logging.info("Not for sale")
        game_price, for_sale = not_for_sale(soup, pre_purchase)
        #logging.debug(f"[After not_for_sale function]{game_price} {for_sale}")
        return game_name.text.strip(), game_price, image_url, for_sale, has_demo, False
      if not "$" in game_price.text.strip():
        logging.info("$ not found -- demo div")
        free_to_play = free_to_play_check(soup)
        if free_to_play:
          logging.info("Free to play")
          game_price = "$0"
          for_sale = True
          return game_name.text.strip(), game_price, image_url, for_sale, has_demo, bundle
        else:
          logging.info("Not free to play")
          game_price = soup.find_all("div", class_="game_purchase_price price")
          game_price = game_price[1]
      for_sale = True
      return game_name.text.strip(), game_price.text.strip(), image_url, for_sale, has_demo, bundle
  except:
    logging.info("Error scraping page")
    logging.info(traceback.format_exc())
    return "Error", "Error", "Error", "Error", "Error"

def free_to_play_check(soup):
  game_price = soup.find("div", class_="game_purchase_price price")
  if game_price is not None:
    if "Free" in game_price.text:
      return True
    else:
      return False


def pre_purchase_check(soup):
  pre_purchase = soup.find_all("div", class_="game_area_purchase_game")
  for p in pre_purchase:
    title = p.find("h1")
    if title == None:
      continue
    if "Pre-Purchase" in title.text:
      return True
  else:
    return False


def bundle_scrape(url):
  r = requests.get(url)
  soup = BeautifulSoup(r.text, "html.parser")
  #name = <h2 class="pageheader">
  #price = <div class="discount_final_price">
  bundle_name = soup.find("h2", class_="pageheader")
  bundle_price = soup.find("div", class_="discount_final_price")
  for_sale = True
  return bundle_name.text.strip(), bundle_price.text.strip(), for_sale


def discount_check(soup) -> bool:
  section = soup.find_all("div", class_="game_purchase_action")
  for index,s in enumerate(section):
    not_discount = s.find(
      "div", class_="discount_block game_purchase_discount no_discount")
    if not_discount == None:
      pass
    elif not_discount != None:
      print("found the 'no discount' div")
      return False
    logging.info("Did not find 'no discount' div")
    discount = s.find("div", class_="discount_final_price")
    if index==0 and discount==None:
      logging.info("first div is not a discount")
      break
    else:
      discount = True
      return discount
  else:
    discount = False
    return discount


def discount_price(soup) -> str:
  section = soup.find_all("div", class_="game_purchase_action")
  for s in section:
    discount = s.find("div", class_="discount_final_price")
    if discount == None:
      continue
    if discount:
      game_price = discount
      return game_price


def not_for_sale(soup, pre):
  try:
    if pre:
      game_price = soup.find("div", class_="game_purchase_price price")
      game_price = game_price.text.strip()
      for_sale = False
      return game_price, for_sale
    else:
      not_for_sale = soup.find("div",
                               class_="game_area_comingsoon game_area_bubble")
      when = not_for_sale.find_all("span")
      when = when[:-1]
      year = when[1].text
      for_sale = False
      game_price = f"Not for Sale until {year}"
  except:
    game_price = "Not for sale"
    for_sale = False
  finally:
    return game_price, for_sale


def purge_old_tokens() -> None:
  try:
    expire_grace = datetime.datetime.now()
    expire_grace = expire_grace + datetime.timedelta(hours=1)
    old_token = expire_grace + datetime.timedelta(hours=4)
    matches = db.prefix("token")
    count = 0
    for match in matches:
      expiry_time = db[match]["token_expiration_time"]
      expiry_time = datetime.datetime.strptime(expiry_time,
                                               "%m-%d-%Y %I:%M:%S %p")
      if db[match]["token_spent"] == True:
        if expiry_time > expire_grace:
          del db[match]
          count += 1
          logging.info("Token Purged")
      elif expiry_time > old_token:
        del db[match]
        count += 1
        logging.info("Token Purged")
    logging.info(f"{count} Tokens Purged")
  except:
    logging.info("Error purging old tokens")
    pass


def compare() -> None:
  try:
    string_time, PT_time = time_get()
    count = 0
    matches = db.prefix("game")
    user_list = db.prefix("user")
    for match in matches:
      username = db[match]["username"]
      for user in user_list:
        if db[user]["username"] == username:
          email = db[user]["email"]
      url = db[match]["url"]
      logging.info(f"==Scraping {db[match]['game_name']}==")
      name, new_price, image_url, for_sale, has_demo, bundle = scrape(url)
      logging.info(f"{name} {new_price} For Sale:{for_sale} Demo:{has_demo}")
      if db[match]["has_demo"] == False and has_demo == True:
        db[match]["has_demo"] = True
        logging.info(f"{name} 'has_demo' value updated to true")
      elif db[match]["has_demo"] == True and has_demo == False:
        db[match]["has_demo"] = False
        logging.info(f"{name} 'has_demo' value updated to false")
      if for_sale and db[match]["for_sale"] == False:
        count += 1
        logging.info(f"{db[match]['game_name']} is now for sale!")
        price_change_mail(email, "0", new_price, "0", url, name, image_url, for_sale)
        db[match]["for_sale"] = True
        db[match]["price"] = new_price
        db[match]["price_change_date"] = string_time
        db[match]["last_updated"] = string_time
        break
      elif not for_sale and db[match]["for_sale"] == False:
        pass
      else:
        new_price = float(new_price[1:])
        old_price = float(db[match]["price"][1:])
        percent_change = round((new_price - old_price) / old_price * 100, 2)
        target_percent = float(db[match]["target_percent"])
      if for_sale:
        if new_price != old_price:
          count += 1
          if percent_change <= target_percent:
            db[match]["old_price"] = f"${old_price}"
            db[match]["price"] = f"${new_price}"
            db[match]["percent_change"] = f"{percent_change}"
            db[match]["price_change_date"] = string_time
            db[match]["last_updated"] = string_time
            logging.info(
              f"{name} - {new_price} - decreased by {percent_change}%")
            price_change_mail(email, old_price, new_price, percent_change, url,
                              name, image_url, for_sale)
          else:
            db[match]["old_price"] = f"${old_price}"
            db[match]["old_price"] = f"${old_price}"
            db[match]["price"] = f"${new_price}"
            db[match]["percent_change"] = f"{percent_change}"
            db[match]["price_change_date"] = string_time
            db[match]["last_updated"] = string_time
            logging.info(f"{name} Price increased by {percent_change}%")
        else:
          logging.info(f"=={name} Price not changed==")
      elif not for_sale:
        logging.info(f"=={name} still not for sale==")
        continue
    logging.info(f"**{count} Prices Updated**")
  except:
    trace = traceback.format_exc()
    logging.error(trace)
    logging.info("Error updating prices!")
    pass


def price_change_mail(recipent, old, new, per, url, name, image_url,
                      for_sale) -> None:
  if for_sale:
    with open(f"{PATH}price_change.html", "r") as f:
      template = f.read()
  elif not for_sale:
    with open(f"{PATH}for_sale.html", "r") as f:
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
      expiry_time = datetime.datetime.strptime(expiry_time,
                                               "%m-%d-%Y %I:%M:%S %p")
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

def wishlist_process(steamID, username) -> None:
  logging.info(f"Processing wishlist for user: {username}")
  page = 0
  wishlist = {}
  wishlist_url = f"https://store.steampowered.com/wishlist/profiles/{steamID}/wishlistdata"
  try:
    while True:
      response = requests.get(wishlist_url, params={"p": page})
      if response.status_code == 500:
        logging.info("Error: Account Privacy settings are probably blocking wishlist lookup.")
        break
      data = response.json()
      if not data:
        break
      wishlist.update(data)
      page += 1
    logging.info(f"Wishlist has {page} pages. Processing...")
    wishlist_url = {}
    for game_id, game in wishlist.items():
      if game_id == "1675200":
        continue
      game_name = game["name"]
      wishlist_url[game_id] = game_name
    wishlist_url = dupe_check(wishlist_url, username)
    count = len(wishlist_url)
    logging.info(f"Processing {count} games from wishlist...")
    string_time, PT_time = time_get()
    matches = db.prefix("game")
    for game_id in wishlist_url:
      url = f"https://store.steampowered.com/app/{game_id}"
      name, price, image_url, for_sale, has_demo, bundle = scrape(url)
      if for_sale:
        price_t = price
        price_t = float(price_t[1:])
        target_price = round(price_t - (price_t * 0.15), 2)
        target_price = f"${target_price:.2f}"
      else:
        target_price = "$0"
      for match in matches:
        if db[match]["game_name"] == name and db[match]["username"] == username:
          db[match]["wishlist"] = True
          logging.info(f"Already loaded: {name}")
          time.sleep(5)
          break
      else:
        logging.info(f"Adding {name} to db")
        game_key = "game" + str(random.randint(100_000_000, 999_999_999))
        db[game_key] = {
          "game_name": name,
          "price": price,
          "url": url,
          "username": username,
          "bundle": False,
          "image_url": image_url,
          "old_price": "$0",
          "percent_change": "0",
          "for_sale": for_sale,
          "target_percent": "-10",
          "target_price": target_price,
          "price_change_date": "Never",
          "wishlist": True,
          "has_demo": has_demo,
          "date_added": string_time
          }
        time.sleep(1)
        continue
    logging.info("====WISHLIST=RUN=COMPLETE====")
  except:
    print(traceback.format_exc())
    logging.info("Error: Unable to fetch wishlist data.")

def dupe_check(wishlist_list, username):
    db_game_names = {db[match]["game_name"] for match in db.prefix("game") if db[match]["username"] == username}
    for game_id, game_name in wishlist_list.copy().items():
        if game_name in db_game_names:
            logging.info(f"Duplicate: {game_name}")
            del wishlist_list[game_id]
    return wishlist_list
        