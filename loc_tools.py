from bs4 import BeautifulSoup
import requests, random, hashlib, string, os, datetime, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, PackageLoader
import smtplib
from flask import g

from __init__ import app
from databaseMan import before_request, close_db

PATH = "static/html/"
logging.basicConfig(filename='app.log', level=logging.DEBUG)


class GameScraper:

  def __init__(self, url):
    self.url = url
    self.soup = self.get_soup()
    self.imageURL = self.image_url()
    self.bundle = self.bundle_check()
    self.name = None
    self.price = None
    self.has_demo = self.demo_check()
    self.discount = self.discount_check()
    self.pre_purchase = self.pre_purchase_check()
    self.for_sale = self.for_sale_check()
    self.free_to_play = self.free_to_play_check()

    if not self.bundle:
      self.name = self.game_name()
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

  def get_soup(self) -> str:
    r = requests.get(self.url)
    return BeautifulSoup(r.text, "html.parser")

  def image_url(self) -> str:
    image = self.soup.find("link", rel="image_src").get("href")
    return image.split("?t=")[0]

  def bundle_check(self) -> str:
    bundle_find = self.soup.find(
      "div", class_="game_area_purchase_game bundle ds_no_flags")
    if bundle_find is not None:
      logging.debug("Bundle found!")
      return True
    else:
      logging.debug("Bundle not found!")
      return False

  def bundle_info(self) -> str:
    bundle_name = self.soup.find("h2", class_="pageheader")
    bundle_price = self.soup.find("div", class_="discount_final_price")
    return bundle_name.text.strip(), bundle_price.text.strip()

  def game_name(self) -> str:
    game_name = self.soup.find("div", class_="apphub_AppName")
    return game_name.text.strip()

  def game_price(self) -> str:
    if self.has_demo:
      game_price = self.soup.find_all("div", class_="game_purchase_price price")
      for index, price in enumerate(game_price):
        if price.get("data-price-final"):
          game_price = game_price[index]
      return game_price.text.strip()
    else:
      game_price = self.soup.find("div", class_="game_purchase_price price")
      return game_price.text.strip()

  def for_sale_check(self) -> bool:
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

  def not_for_sale_info(self) -> str:
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

  def free_to_play_check(self) -> bool:
    game_price = self.soup.find("div", class_="game_purchase_price price")
    if game_price is not None:
      if "Free" in game_price.text:
        return True
    return False

  def pre_purchase_check(self) -> bool:
    pre_purchase = self.soup.find_all("div", class_="game_area_purchase_game")
    for p in pre_purchase:
      title = p.find("h1")
      if title == None:
        continue
      if "Pre-Purchase" in title.text:
        return True
    else:
      return False

  def demo_check(self) -> bool:
    demo = self.soup.find("div", class_="game_area_purchase_game demo_above_purchase")
    if demo == None:
      return False
    else:
      return True

  def discount_check(self) -> bool:
    section = self.soup.find_all("div", class_="game_purchase_action")
    for index, s in enumerate(section):
      not_discount = s.find(
        "div", class_="discount_block game_purchase_discount no_discount")
      if not_discount == None:
        pass
      elif not_discount != None:
        return False
      discount = s.find("div", class_="discount_final_price")
      if index == 0 and discount == None:
        continue
      elif self.has_demo and index == 1 and discount != None:
        return True
      elif self.has_demo == False and discount != None and index == 0:
        return True
    return False

  def discount_price(self) -> str:
    section = self.soup.find_all("div", class_="game_purchase_action")
    for s in section:
      discount = s.find("div", class_="discount_final_price")
      if discount == None:
        continue
      if discount:
        game_price = discount
        return game_price.text.strip()


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


def confirm_mail(recipient, token, type) -> None:
  URL = "https://scraping-steam-prices.thechaz.repl.co/"
  with open(f"{PATH}confirm_token.html", "r") as f:
    template = f.read()
  if type not in ["confirm", "recovery"]:
    logging.debug(f"{type} is not a valid option")
    return
  if type == "confirm":
    template = template.replace("{token}", token)
    template = template.replace("{desc}", "Confirm your Email Address by clicking below.")
    template = template.replace("{url}", f"{URL}/")
    template = template.replace("{type}", type)
  elif type == "recovery":
    template = template.replace("{token}", token)
    template = template.replace("{desc}", "Recover your password by clicking the link below.")
    template = template.replace("{url}", f"{URL}/")
    template = template.replace("{type}", type)
  server = os.environ.get("SMTP_SERVER")
  port = 587
  s = smtplib.SMTP(host=server, port=port)
  s.starttls()
  username = os.environ['mailUsername']
  password = os.environ['mailPassword']
  s.login(username, password)
  msg = MIMEMultipart()
  msg['To'] = recipient
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

def gen_unique_token(username) -> str:
  token = tokenGet().lower()
  current_time = datetime.datetime.now()
  expiration_time = current_time + datetime.timedelta(minutes=30)
  expiration_str = expiration_time.strftime("%m-%d-%Y %I:%M:%S %p")
  request_date_str = current_time.strftime("%m-%d-%Y %I:%M:%S %p")
  base = g.base
  users = base.get_all_users(username)
  email = next((user["email"] for user in users if user["username"] == username), None)
  if not email:
    logging.debug("No email found for user")
    return
  db_key = base.add_token(token, 
                          request_date_str, 
                          expiration_str, 
                          username, 
                          email
  )
  return db_key

def tokenGet() -> str:
  return ''.join(
    random.choice(string.ascii_letters + string.digits) for _ in range(30))


def token_expiration(token, tokens) -> bool:
  for t in tokens:
    if t["token"] == token and not token["token_spent"]:
      expiry_time = datetime.datetime.strptime(t["token_expiration_time"], "%m-%d-%Y %I:%M:%S %p")
      return datetime.datetime.now() > expiry_time


def time_get() -> str:
  PT_time = datetime.datetime.now() - datetime.timedelta(hours=8)
  string_time = PT_time.strftime("%m-%d-%Y %I:%M:%S %p")
  return string_time, PT_time

def wishlist_process(steamID, username) -> None:
    with app.app_context():
      before_request()
      logging.debug(f"Processing wishlist for user: {username}")
      page = 0
      wishlist = {}
      wishlist_url = f"https://store.steampowered.com/wishlist/profiles/{steamID}/wishlistdata"
      try:
          base = g.base
          matches = base.get_all_games()
          while True:
              response = requests.get(wishlist_url, params={"p": page})
              if response.status_code == 500:
                  logging.debug("Error: Account Privacy settings are probably blocking wishlist lookup.")
                  break
              data = response.json()
              if not data:
                  break
              wishlist.update(data)
              page += 1
          logging.debug(f"Wishlist has {page} pages.")
          wishlist_url = {game_id: game["name"] for game_id, game in wishlist.items() if game_id != "1675200"}
          wishlist_url = dupe_check(wishlist_url, username)
          logging.info(f"Processing {len(wishlist_url)} games from wishlist...")
          string_time, _ = time_get()
          for game_id, game in wishlist_url.items():
              url = f"https://store.steampowered.com/app/{game_id}"
              s = GameScraper(url)
              game_name = s.name
              if s.for_sale:
                  price_t = s.price
                  price_t = float(price_t[1:])
                  target_price = round(price_t - (price_t * 0.15), 2)
                  target_price = f"${target_price:.2f}"
              else:
                  target_price = "$0"
              if any(match["game_name"] == game_name for match in matches):
                  logging.debug(f"Already loaded: {game}")
              else:
                  logging.debug(f"Adding {game_name} to db")
                  base.add_game(
                      game,
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
          logging.info("====WISHLIST RUN COMPLETE ====")
      except Exception as e:
          logging.error(f"Error: {e}")
          logging.error("Error: Unable to fetch wishlist data.")
      finally:
        close_db()


def dupe_check(wishlist_list, username):
    base = g.base
    db_game_names = {match["game_name"] for match in base.get_games_by_username(username)}
    duplicates = {game_id: game for game_id, game in wishlist_list.items() if game in db_game_names}
    wishlist_list = {game_id: game for game_id, game in wishlist_list.items() if game not in db_game_names}
    logging.info(f"Duplicate check: {len(duplicates)} games skipped.")
    return wishlist_list

def chores() -> None:
  now_str, now = time_get()
  try:
    with app.app_context():
      before_request()
      logging.info(f"Chores starting at {now_str}")
      purge_old_tokens()
      compare()
      logging.info("Chores finished")
  except Exception as e:
    close_db(e)
    logging.debug(f"Chores failed! {e}")
  finally:
      close_db()
      after_str, after = time_get()
      time_taken = after - now
      time_taken_secs = round(time_taken.total_seconds(), 2)
      if time_taken_secs > 60:
          time_taken_mins = round(time_taken_secs / 60, 2)
          logging.info(f"Chores took {time_taken_mins} minutes")
      else:
          logging.info(f"Time taken: {time_taken_secs} seconds")
      logging.info(f"Chores finished at {after_str}")
      logging.info("==== CHORES RUN COMPLETE ====")

def purge_old_tokens() -> None:
  try:
    expire_grace = datetime.datetime.now()
    expire_grace = expire_grace + datetime.timedelta(hours=2)
    base = g.base
    expired_tokens = [m for m in base.get_all_tokens() if m["token_spent"] or datetime.datetime.strptime(m["token_expiration_time"], "%m-%d-%Y %I:%M:%S %p") <= expire_grace]
    for token in expired_tokens:
      base.delete_token(token)
    logging.info(f"{len(expired_tokens)} Tokens Purged")
  except Exception as e:
    logging.debug(e)

def username_to_email(username) -> str:
  try:
    base = g.base
    user = base.get_user_by_username(username)
    if not user:
      raise Exception("User not found")
    return user["email"]
  except Exception as e:
    logging.debug(e)

def compare() -> None:
    base = g.base
    matches = base.get_all_games()
    email_digest = {}
    count = 0
    for match in matches:
        try:
            email_digest, count = update_game_data(match, email_digest, count)
        except Exception as e:
            logging.debug(e)
    price_change_mail(email_digest)
    logging.info(f"{count} prices updated")

def update_game_data(match, email_digest, count):
    base = g.base
    string_time, _ = time_get()
    s = GameScraper(match["url"])
    username = match["username"]
    email = username_to_email(username)
    logging.debug(f"==Scraping {match['game_name']}==")
    try:
      if match["has_demo"] != s.has_demo:
        base.update_game(match["game_name"], "has_demo", s.has_demo)
        logging.info(f"{s.name} 'has_demo' value updated to {s.has_demo}")
      if s.for_sale and not match["for_sale"]:
          count += 1
          if s.for_sale:
              logging.info(f"{s.name} is now for sale!")
              game_data = {
                  'old_price': "0",
                  'new_price': s.price,
                  'percent_change': "0",
                  'url': match["url"],
                  'image_url': s.imageURL,
                  'for_sale': s.for_sale,
                  'type': "on_sale"
              }
              email_digest.setdefault(username, {'email': email, 'games': {}})
              email_digest[username]['games'][s.name] = game_data
          elif not s.for_sale and match["for_sale"]:
              logging.info(f"Weird! {s.name} is no longer for sale!")
              base.update_game(s.name, "price", "$0")
              base.update_game(s.name, "old_price", "$0")
              base.update_game(s.name, "percent_change", "0")
          base.update_game(s.name, "for_sale", s.for_sale)
          base.update_game(s.name, "price_change_date", string_time)
      if s.for_sale and s.price != match["price"]:
          new_price = float(s.price[1:])
          old_price = float(match["price"][1:])
          percent_change = round((new_price - old_price) / old_price * 100, 2)
          target_percent = float(match["target_percent"])
          if percent_change <= target_percent:
              count += 1
              base.update_game(s.name, "old_price", f"${old_price}")
              base.update_game(s.name, "price", f"${new_price}")
              base.update_game(s.name, "percent_change", f"{percent_change}")
              base.update_game(s.name, "price_change_date", string_time)
              logging.info(f"{s.name} - {new_price} - decreased by {percent_change}%")
              game_data = {
                  'old_price': old_price,
                  'new_price': new_price,
                  'percent_change': percent_change,
                  'url': match["url"],
                  'image_url': s.imageURL,
                  'for_sale': s.for_sale,
                  'type': "price_change"
              }
              email_digest.setdefault(username, {'email': email, 'games': {}})
              email_digest[username]['games'][s.name] = game_data
          else:
              base.update_game(s.name, "old_price", f"${old_price}")
              base.update_game(s.name, "price", f"${new_price}")
              base.update_game(s.name, "percent_change", f"{percent_change}")
              base.update_game(s.name, "price_change_date", string_time)
              logging.info(f"{s.name} Price increased by {percent_change}%")
      elif not s.for_sale:
          logging.debug(f"=={s.name} still not for sale==")
      elif s.for_sale and s.price == match["price"]:
          logging.debug(f"=={s.name} Price not changed==")
      return email_digest, count
    except Exception as e:
        logging.debug(e)