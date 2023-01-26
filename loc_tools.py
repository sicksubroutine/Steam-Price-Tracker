from bs4 import BeautifulSoup
import requests, random, hashlib, string, os
from replit import db
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

PATH = "static/html/"

def scrape(url, bundle=False):
  headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
  r = requests.get(url, headers=headers)
  soup = BeautifulSoup(r.text, "html.parser")
  image = soup.find("link", rel="image_src").get("href")
  image_url = image.split("?t=")[0]
  if bundle:
    #name = <h2 class="pageheader">
    #price = <div class="discount_final_price">
    bundle_name = soup.find("h2", class_="pageheader")
    bundle_price = soup.find("div", class_="discount_final_price")
    return (bundle_name.text.strip(), bundle_price.text.strip())
  else:
    #game name = <div class="apphub_AppName">
    game_name = soup.find("div", class_="apphub_AppName")
    #game price = <div class="game_purchase_price price">
    game_price = soup.find("div", class_="game_purchase_price price")
    if game_price == None:
      game_price = "Not for Sale"
      return game_name.text.strip(), game_price, image_url
    else:
      return game_name.text.strip(), game_price.text.strip(), image_url
  
def compare():
  matches = db.prefix("game")
  for match in matches:
    url = db[match]["url"]
    bundle = db[match]["bundle"]
    if bundle == "Not a Bundle":
      bundle = False
    else:
      bundle = True
    name, new_price, image_url = scrape(url, bundle)
    new_price = float(new_price[1:])
    old_price = float(db[match]["price"][1:])
    
    percent_change = (new_price - old_price) / old_price * 100
    
    if new_price != old_price:
      if percent_change <= -10:
        
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
        print(f"{name} - {new_price} - decreased by {percent_change}%")
        sendMail(email, old_price, new_price, percent_change, url, name, image_url)
      else:
        db[match]["old_price"] = f"${old_price}"
        db[match]["price"] = f"${new_price}"
        db[match]["percent_change"] = f"{percent_change}"
        print(f"{name} Price increased by {percent_change}%")
    else:
      print(f"{name} Price not changed")
      continue

def sendMail(recipent, old, new, per, url, name, image_url):
  with open(f"{PATH}email_template.html", "r") as f:
    template = f.read()
  template = template.replace("{image_url}", image_url)
  template = template.replace("{percent_change}", per)
  template = template.replace("{desc}", name)
  template = template.replace("{link}", url)
  template = template.replace("{old}", old)
  template = template.replace("{new}", new)
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
  del msg
  
def saltPass(pwd, salt):
  pwd = (pwd + str(salt)).encode('utf-8')
  return hashlib.sha256(pwd).hexdigest()

def saltGet():
  return ''.join(random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(30))