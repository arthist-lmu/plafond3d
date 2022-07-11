import requests
import requests_cache
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import os
import time


requests_cache.install_cache('scrape_cache')


def extract_contents(r):
    if r.status_code == 200:
        r.content
    else:
        print("Couldn't load website, status code: " + r.status_code)
        exit(1)

    soup = BeautifulSoup(r.content, 'html.parser')

    print(soup.prettify())

    s = soup.find('div', class_='react-es-results')
    print(s)
    content = soup.find_all('list-card-container')

    print(content)

    # list-card-container


for x in range(1, 2):
    url = "https://www.pop.culture.gouv.fr/search/list?resPage=" + str(x) + "&periode=%5B%2217e+si%C3%A8cle%22%2C%2216e+si%C3%A8cle%22%5D&type=%5B%22plafond%22%5D"
    print(url)
    #r = requests.get(url, timeout=(3, 27))
    os.environ["TMPDIR"] = "tmp"
    
    options = Options()
    options.add_argument("--headless")
    browser = webdriver.Firefox(options=options, executable_path=r'./geckodriver')
    browser.get(url)
    html = browser.page_source
    time.sleep(2)
    print(html)

    # close web browser
    browser.close()
    #extract_contents(r)
    #soup = BeautifulSoup(html, 'lxml')
