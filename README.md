# Plafond3d

Plafond3D is a collaborative project of DNF and ANR to combine national research data of ceiling paintings and integrate 3D-images 

The project will produce of a website, which combines different data sources for ceiling paintings in France and Germany.

The code in this repository is about the data refinement and matching.

# Interesting aspects of our dataset
* [Neue Residenz (Passau)]([url](https://www.wikidata.org/wiki/Q1979730))
* [Ceiling painting in the staircase of the New Residence Passau]([url](https://www.wikidata.org/wiki/Q122702246))
* [Map of all buildings]([url](https://query.wikidata.org/embed.html#%23title%3Alocation%20of%20items%20with%20property%20P10626%20statements%0A%23defaultView%3AMap%7B%22hide%22%3A%5B%22%3Fcoordinates%22%5D%7D%0ASELECT%20DISTINCT%20%3Fsite%20%3FsiteLabel%20%3Fcoordinates%20%3Fimage%20%3Fvalue%0AWHERE%20%0A%7B%0A%20%20%3Fsite%20wdt%3AP10626%20%3Fvalue%3B%20wdt%3AP625%20%3Fcoordinates.%0A%20%20OPTIONAL%20%7B%20%3Fsite%20wdt%3AP18%20%3Fimage%20%7D%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D))
* [Map of Birthplaces]([url](https://query.wikidata.org/index.html#%23defaultView%3AMap%0ASELECT%20%3Fperson%20%3FpersonLabel%20%3Fplaceofbirth%20%3FplaceofbirthLabel%20%3FgeoCoord%20%3Fimage%20WHERE%20%7B%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%20%20%3Fperson%20p%3AP10626%20%3Fstatement0.%0A%20%20%3Fstatement0%20%28ps%3AP10626%29%20_%3AanyValueP10626.%0A%20%20OPTIONAL%20%7B%0A%20%20%3Fperson%20wdt%3AP18%20%3Fimage.%0A%20%20%3Fperson%20wdt%3AP19%20%3Fplaceofbirth.%0A%20%20%3Fplaceofbirth%20wdt%3AP625%20%3FgeoCoord.%0A%20%20%20%20%7D%0A%7D%0ALIMIT%2010000))
* [Confession]([url](https://query.wikidata.org/index.html#SELECT%20%3Fperson%20%3FpersonLabel%20%3FconfessionLabel%20WHERE%20%7B%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%20%20%3Fperson%20p%3AP10626%20%3Fstatement0.%0A%20%20%3Fstatement0%20%28ps%3AP10626%29%20_%3AanyValueP10626.%0A%20%20%3Fperson%20wdt%3AP140%20%3Fconfession.%0A%7D%0ALIMIT%2010000))
* [Familiy tree of Henry of Palatine]([url](https://www.entitree.com/en/family_tree/Q86138))

# Setup

Use a python [venv](https://docs.python.org/3/library/venv.html) and set up [poetry](https://python-poetry.org/) to get started.

The web scraper is using selenium, and therefore needs to be configured before running it. Download your correct geckodriver [here](https://github.com/mozilla/geckodriver/releases).

# Data sources

## Deckenmalerei.eu

## A heurist.org instance

## Pop.culture.gov.fr
Plafond query

[Plafond query](https://www.pop.culture.gouv.fr/search/list?type=%5B%22plafond%22%5D&periode=%5B%2217e%20si%C3%A8cle%22%2C%2218e%20si%C3%A8cle%22%2C%224e%20quart%2017e%20si%C3%A8cle%22%2C%224e%20quart%2018e%20si%C3%A8cle%22%2C%221er%20quart%2017e%20si%C3%A8cle%22%2C%221%C3%A8re%20moiti%C3%A9%2017e%20si%C3%A8cle%22%2C%223e%20quart%2017e%20si%C3%A8cle%22%2C%222e%20moiti%C3%A9%2018e%20si%C3%A8cle%22%2C%222e%20quart%2017e%20si%C3%A8cle%22%2C%221%C3%A8re%20moiti%C3%A9%2018e%20si%C3%A8cle%22%2C%222e%20quart%2018e%20si%C3%A8cle%22%2C%2217e%20si%C3%A8cle%20%28%3F%29%22%2C%221er%20quart%20du%2017e%20si%C3%A8cle%22%2C%223e%20quart%2018e%20si%C3%A8cle%22%2C%22limite%2016e%20si%C3%A8cle%2017e%20si%C3%A8cle%22%2C%22milieu%2017e%20si%C3%A8cle%22%2C%22milieu%2018e%20si%C3%A8cle%22%2C%221%C3%A8re%20moiti%C3%A9%2017e%20si%C3%A8cle%20%28%3F%29%22%2C%222e%20moiti%C3%A9%2017e%20si%C3%A8cle%20%28%3F%29%22%2C%224e%20quart%2017e%20si%C3%A8cle%20%28%3F%29%22%2C%2217e%20si%C3%A8cle%20%28suppos%C3%A9%29%22%2C%2217e%20si%C3%A8cle%2C%2018e%20si%C3%A8cl)
