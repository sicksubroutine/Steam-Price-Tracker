from bs4 import BeautifulSoup
import requests, random, hashlib, string, os, datetime, time, logging, traceback
from replit import db
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, PackageLoader
import smtplib

PATH = "static/html/"
logging.basicConfig(filename='app.log', level=logging.INFO)


class GameScraper:

  def __init__(self, url):
    self.url = url
    self.soup = self.get_soup()
    self.image_url = self.image_url()
    self.bundle = self.bundle_check()
    self.name = None
    self.price = None
    self.pre_purchase = self.pre_purchase_check()
    self.has_demo = self.demo_check()
    self.discount = self.discount_check()
    self.for_sale = self.for_sale_check()
    self.free_to_play = self.free_to_play_check()

    if not self.bundle:
      self.name = self.game_name()
      logging.info(self.name)
      if self.for_sale:
        if self.free_to_play:
          self.price = "$0"
        elif self.discount:
          self.price = self.discount_price()
        else:
          self.price = self.game_price()
      else:
        self.price = self.not_for_sale_info()
    else:
      self.name, self.price = self.bundle_info()

  def get_soup(self):
    r = requests.get(self.url)
    return BeautifulSoup(r.text, "html.parser")

  def image_url(self):
    image = self.soup.find("link", rel="image_src").get("href")
    return image.split("?t=")[0]

  def bundle_check(self):
    bundle_find = self.soup.find(
      "div", class_="game_area_purchase_game bundle ds_no_flags")
    if bundle_find is not None:
      logging.debug("Bundle found!")
      return True
    else:
      logging.debug("Bundle not found!")
      return False

  def bundle_info(self):
    bundle_name = self.soup.find("h2", class_="pageheader")
    bundle_price = self.soup.find("div", class_="discount_final_price")
    return bundle_name.text.strip(), bundle_price.text.strip()

  def game_name(self):
    game_name = self.soup.find("div", class_="apphub_AppName")
    return game_name.text.strip()

  def game_price(self):
    if self.has_demo:
      game_price = self.soup.find_all("div", class_="game_purchase_price price")
      for index, price in enumerate(game_price):
        if price.get("data-price-final"):
          game_price = game_price[index]
      return game_price.text.strip()
    else:
      game_price = self.soup.find("div", class_="game_purchase_price price")
      return game_price.text.strip()

  def for_sale_check(self):
    game_price = self.soup.find("div", class_="game_purchase_price price")
    if self.pre_purchase:
      return False
    if game_price is None and self.discount:
      return True
    elif game_price is None:
      logging.debug("Not for sale!")
      return False
    else:
      return True

  def not_for_sale_info(self):
    try:
      not_for_sale = self.soup.find(
        "div", class_="game_area_comingsoon game_area_bubble")
      when = not_for_sale.find_all("span")
      when = when[:-1]
      year = when[1].text
      game_price = f"Not for Sale until {year}"
      return game_price
    except:
      return "Not for Sale"

  def free_to_play_check(self):
    game_price = self.soup.find("div", class_="game_purchase_price price")
    if game_price is not None:
      if "Free" in game_price.text:
        return True
    return False

  def pre_purchase_check(self):
    pre_purchase = self.soup.find_all("div", class_="game_area_purchase_game")
    for p in pre_purchase:
      title = p.find("h1")
      if title == None:
        continue
      if "Pre-Purchase" in title.text:
        return True
    else:
      return False

  def demo_check(self):
    demo = self.soup.find("div", class_="game_area_purchase_game demo_above_purchase")
    if demo == None:
      return False
    else:
      return True

  def discount_check(self):
    section = self.soup.find_all("div", class_="game_purchase_action")
    for index, s in enumerate(section):
      not_discount = s.find(
        "div", class_="discount_block game_purchase_discount no_discount")
      if not_discount == None:
        pass
      elif not_discount != None:
        logging.debug("found the 'no discount' div")
        return False
      discount = s.find("div", class_="discount_final_price")
      if index == 0 and discount == None:
        break
      else:
        return True

    return False

  def discount_price(self):
    section = self.soup.find_all("div", class_="game_purchase_action")
    for s in section:
      discount = s.find("div", class_="discount_final_price")
      if discount == None:
        continue
      if discount:
        game_price = discount
        return game_price.text.strip()


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
          logging.debug("Token Purged")
      elif expiry_time > old_token:
        del db[match]
        count += 1
        logging.debug("Token Purged")
    logging.info(f"{count} Tokens Purged")
  except:
    logging.info("Error purging old tokens")
    trace = traceback.format_exc()
    logging.debug(trace)


def compare() -> None:
  try:
    string_time, PT_time = time_get()
    count = 0
    num = 0
    email_digest = {}
    matches = db.prefix("game")
    logging.debug(f"{len(matches)}")
    user_list = db.prefix("user")
    for match in matches:
      username = db[match]["username"]
      for user in user_list:
        if db[user]["username"] == username:
          email = db[user]["email"]
      url = db[match]["url"]
      logging.debug(f"==Scraping {db[match]['game_name']}==")
      num += 1
      s = GameScraper(url)
      game_name = s.name
      new_price = s.price
      image_url = s.image_url
      for_sale = s.for_sale
      has_demo = s.has_demo
      bundle = s.bundle
      logging.debug(
        f"{game_name} {new_price} For Sale:{for_sale} Demo:{has_demo}")
      if db[match]["has_demo"] == False and has_demo == True:
        db[match]["has_demo"] = True
        logging.info(f"{game_name} 'has_demo' value updated to true")
      elif db[match]["has_demo"] == True and has_demo == False:
        db[match]["has_demo"] = False
        logging.info(f"{game_name} 'has_demo' value updated to false")
      if for_sale and db[match]["for_sale"] == False:
        count += 1
        logging.info(f"{db[match]['game_name']} is now for sale!")
        # Replacing multiple emails with single digest email
        game_data = {
          'old_price': "0",
          'new_price': new_price,
          'percent_change': "0",
          'url': url,
          'image_url': image_url,
          'for_sale': for_sale,
          'type': "on_sale"
        }
        if username in email_digest:
          email_digest[username]['games'][game_name] = game_data
        else:
          email_digest[username] = {
            'email': email,
            'games': {
              game_name: game_data
            }
          }
        db[match].update({
          "for_sale": True,
          "price": new_price,
          "price_change_date": string_time
        })
        continue
      elif not for_sale and db[match]["for_sale"] == False:
        pass
      else:
        try:
          new_price = float(new_price[1:])
          logging.debug(f"New Price: {new_price}")
          old_price = float(db[match]["price"][1:])
          logging.debug(f"Old Price: {old_price}")
          percent_change = round((new_price - old_price) / old_price * 100, 2)
          target_percent = float(db[match]["target_percent"])
        except ZeroDivisionError:
          logging.info("Free Game - Zero Division Error")
          pass
      if for_sale:
        if new_price != old_price:
          count += 1
          if percent_change <= target_percent:
            db[match].update({
              "old_price": f"${old_price}",
              "price": f"${new_price}",
              "percent_change": f"{percent_change}",
              "price_change_date": string_time
            })
            logging.info(
              f"{game_name} - {new_price} - decreased by {percent_change}%")
            # Replacing multiple emails with single digest email
            game_data = {
              'old_price': old_price,
              'new_price': new_price,
              'percent_change': percent_change,
              'url': url,
              'image_url': image_url,
              'for_sale': for_sale,
              'type': "price_change"
            }
            if username in email_digest:
              email_digest[username]['games'][game_name] = game_data
            else:
              email_digest[username] = {
                'email': email,
                'games': {
                  game_name: game_data
                }
              }
          else:
            db[match].update({
              "old_price": f"${old_price}",
              "price": f"${new_price}",
              "percent_change": f"{percent_change}",
              "price_change_date": string_time
            })
            logging.info(f"{game_name} Price increased by {percent_change}%")
        else:
          logging.debug(f"=={game_name} Price not changed==")
      elif not for_sale:
        logging.debug(f"=={game_name} still not for sale==")
        continue
    # Send email digest
    price_change_mail(email_digest)
    logging.info(f"**{count} of {num} Prices Updated**")
  except:
    price_change_mail(email_digest)
    logging.info("Error updating prices!")
    trace = traceback.format_exc()
    logging.info(trace)
    logging.info(f"**{count} of {num} Prices Updated**")


def price_change_mail(email_digest) -> None:
  if not email_digest:
    logging.info("No email digest to send!")
    return

  server = os.environ.get("SMTP_SERVER")
  port = 587
  mail_username = os.environ['mailUsername']
  mail_password = os.environ['mailPassword']

  env = Environment(loader=PackageLoader(__name__, 'templates'))
  template = env.get_template('price_change.html')

  for username in email_digest:
    recipient = email_digest[username]['email']
    games = email_digest[username]['games']

    context = {
      'username': username,
      'games': games,
    }

    html = template.render(context)

    msg = MIMEMultipart()
    msg['To'] = recipient
    msg['From'] = os.environ['emailFrom']
    msg['Subject'] = "Steam Price Change Digest"
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP(server, port) as server:
      server.starttls()
      server.login(mail_username, mail_password)
      server.send_message(msg)
    logging.info("User has been emailed a price change digest email.")


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
    logging.debug(f"{type} is not a valid option")
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
  logging.debug("User has been emailed a confirmation email.")
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
  logging.debug(token_expiration_time)
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
  now_str, now = time_get()
  try:
    logging.info(f"Chores starting at {now_str}")
    purge_old_tokens()
    compare()
    after_str, after = time_get()
    time_taken = after - now
    # convert to seconds
    time_taken_secs = round(time_taken.total_seconds(), 2)
    logging.info(f"Chores finished at {after_str}")
    if time_taken_secs > 60:
      time_taken_mins = round(time_taken_secs / 60, 2)
      logging.info(f"Chores took {time_taken_mins} minutes")
    else:
      logging.info(f"Time taken: {time_taken_secs} Seconds")
    logging.info("====CHORES=RUN=COMPLETE====")
  except:
    after_str, after = time_get()
    if time_taken_secs > 60:
      time_taken_mins = round(time_taken_secs / 60, 2)
      logging.info(f"Chores took {time_taken_mins} minutes")
    else:
      logging.info(f"Time taken: {time_taken_secs} Seconds")
    logging.info("====CHORES=RUN=FAILED====")
    pass


def wishlist_process(steamID, username) -> None:
  logging.debug(f"Processing wishlist for user: {username}")
  page = 0
  wishlist = {}
  wishlist_url = f"https://store.steampowered.com/wishlist/profiles/{steamID}/wishlistdata"
  try:
    while True:
      response = requests.get(wishlist_url, params={"p": page})
      if response.status_code == 500:
        logging.debug(
          "Error: Account Privacy settings are probably blocking wishlist lookup."
        )
        break
      data = response.json()
      if not data:
        break
      wishlist.update(data)
      page += 1
    logging.debug(f"Wishlist has {page} pages. Processing...")
    wishlist_url = {}
    for game_id, game in wishlist.items():
      if game_id == "1675200":
        continue
      game_name = game["name"]
      wishlist_url[game_id] = game_name
    wishlist_url = dupe_check(wishlist_url, username)
    logging.info(f"Processing {len(wishlist_url)} games from wishlist...")
    string_time, PT_time = time_get()
    matches = db.prefix("game")
    for game_id in wishlist_url:
      url = f"https://store.steampowered.com/app/{game_id}"
      s = GameScraper(url)
      game_name = s.name
      price = s.price
      image_url = s.image_url
      for_sale = s.for_sale
      has_demo = s.has_demo
      bundle = s.bundle
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
          logging.debug(f"Already loaded: {name}")
          time.sleep(5)
          break
      else:
        logging.debug(f"Adding {name} to db")
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
          "price_change_date": "Never",
          "wishlist": True,
          "has_demo": has_demo,
          "date_added": string_time
        }
        time.sleep(1.5)
        continue
    logging.info("====WISHLIST=RUN=COMPLETE====")
  except:
    logging.info(traceback.format_exc())
    logging.debug("Error: Unable to fetch wishlist data.")


def dupe_check(wishlist_list, username):
  count = 0
  db_game_names = {
    db[match]["game_name"]
    for match in db.prefix("game") if db[match]["username"] == username
  }
  for game_id, game_name in wishlist_list.copy().items():
    if game_name in db_game_names:
      count += 1
      del wishlist_list[game_id]
  logging.info(f"Duplicate check: {count} games skipped.")
  return wishlist_list
