from chrome_scraper.browser import Browser

with Browser(skip_confirmation=True).get_browser() as browser:
    browser.get_url_source("https://bbc.co.uk/football/tables")
    browser.save_tables()
