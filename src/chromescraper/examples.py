from chromescraper.browser import Browser, SimpleBrowser, to_csv, By

# Use the simple browser to load a webpage and save any tables as .csv files
simple_browser = SimpleBrowser()
page = simple_browser.get_page_source("https://www.bbc.co.uk/sport/football/tables")
tables = simple_browser.get_tables(page)
to_csv(tables)

# Use the Selenium driver to open a webpage in Chrome and scrape any tables to .csv files
with Browser(skip_confirmation=True, minimise=False) as browser:
    page = browser.get_page_source("https://www.bbc.co.uk/sport/football/tables")
    tables = browser.get_tables(page)
    to_csv(tables)

    # Load a web page and out out the text of any <h3> elements
    page = browser.get_page_source("https://www.bbc.co.uk/news/")
    for headline in page.find_all("h3"):
        print(headline.text)

    # Click on the "England" hyperlink, find <picture> elements and output
    # the alt attribute of the <img> tag
    el = browser.driver.find_element(by=By.LINK_TEXT, value="England")
    el.click()
    browser.wait_for_page_item(By.TAG_NAME, "picture")

    pictures = browser.driver.find_elements(By.TAG_NAME, "picture")
    for image in pictures:
        img = image.find_element(by=By.TAG_NAME, value="img")
        print(img.get_attribute("alt"))
