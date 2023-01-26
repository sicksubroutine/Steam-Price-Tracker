from bs4 import BeautifulSoup
import requests, random, hashlib, string

def scrape(url):
  headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
  r = requests.get(url, headers=headers)
  soup = BeautifulSoup(r.text, "html.parser")
  #game name = <div class="apphub_AppName">
  game_name = soup.find("div", class_="apphub_AppName")
  #game price = <div class="game_purchase_price price">
  game_price = soup.find("div", class_="game_purchase_price price")
  #TODO: Scrape Game Image
  if game_price == None:
    game_price = "Not for Sale"
    return game_name.text.strip(), game_price
  else:
    return game_name.text.strip(), game_price.text.strip()

def compare(game_name, game_price):
  pass

def saltPass(pwd, salt):
  pwd = (pwd + str(salt)).encode('utf-8')
  return hashlib.sha256(pwd).hexdigest()

def saltGet():
  return ''.join(random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(30))