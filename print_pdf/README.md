# Converting deckenmalerei.eu articles into clean pdfs

* Using the print functionality of modern webbrosers
* A custom media.css file to:
  * reduce visual clutter
  * flatten image slideshows into readable pictures for printed pages
* Automatically parsing deckenmalerei.eu in specific intervals (e.g one year) to re-export the pages

## Libraries used

* **playwright**
* **BeautifulSoup (bs4)**

## Setup

```bash
poetry install
# install the Playwright browser binaries
poetry run playwright install chromium
```

This step is required only once after setting up the project or when updating Playwright to a new major version.

## Development

Testpage:
Aschendorf, Herrenhaus und Amtssitz Altenkamp
<https://www.deckenmalerei.eu/0c728050-c5af-11e9-893a-a37e5cdc9651>
