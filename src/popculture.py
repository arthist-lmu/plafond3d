import requests
import requests_cache
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import os
from os.path import exists
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
    if not exists("cache.html"):
        url = "https://www.pop.culture.gouv.fr/search/list?resPage=" + \
            str(x) + "&periode=%5B%2217e+si%C3%A8cle%22%2C%2216e+si%C3%A8cle%22%5D&type=%5B%22plafond%22%5D"
        print(url)
        #r = requests.get(url, timeout=(3, 27))
        os.environ["TMPDIR"] = "tmp"

        options = Options()
        options.add_argument("--headless")
        browser = webdriver.Firefox(
            options=options, executable_path=r'./geckodriver')
        browser.get(url)
        time.sleep(2)

        html = browser.page_source
        browser.close()

        cache_file = open("cache.html", "w")
        cache_file.write(html)
        cache_file.close()

    else:
        cache_file = open("cache.html", "r")
        html = cache_file.read()
        print("Size of site: " + str(len(html)))
        # close web browser
        soup = BeautifulSoup(html, 'lxml')
        #content = soup.find_all('list-card-container')
        results = soup.find('div', class_='react-es-results').prettify()
        print("Size of site: " + str(len(results)))

#        print(results)
        # extract_contents(r)
