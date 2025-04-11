from chromescraper.browser import Browser, SimpleBrowser, to_csv, By

simple_browser = SimpleBrowser()
page = simple_browser.get_page_source("https://www.bbc.co.uk/sport/football/tables")
tables = simple_browser.get_tables(page)
to_csv(tables)

with Browser(skip_confirmation=True, minimise=False) as browser:
    page = browser.get_page_source("https://www.bbc.co.uk/sport/football/tables")
    tables = browser.get_tables(page)
    to_csv(tables)
    page = browser.get_page_source("https://www.bbc.co.uk/news/")
    for headline in page.find_all("h3"):
        print(headline.text)

    el = browser.driver.find_element(by=By.LINK_TEXT, value="England")
    el.click()
    browser.wait_for_page_item(By.TAG_NAME, "picture")

    pictures = browser.driver.find_elements(By.TAG_NAME, "picture")
    for image in pictures:
        img = image.find_element(by=By.TAG_NAME, value="img")
        print(img.get_attribute("alt"))
