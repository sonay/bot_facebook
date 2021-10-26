import csv
import locale
import logging
import os
import sys
import argparse
from collections import namedtuple
from datetime import datetime
from hashlib import md5
from io import BytesIO
from pathlib import Path

from PIL import Image
from selenium.common.exceptions import TimeoutException, InvalidArgumentException

from exceptions import PrivateAccountException, TemporarilyBannedException
from parsers import PublicAccountScraper

# For Python to parse Turkish datetime properly (to handle localized month and day names)
locale.setlocale(locale.LC_ALL, "tr_TR.UTF8")

_logger = logging.getLogger(__name__)

APP_NAME = "bot_facebook"

MY_MONTH_FORMAT = '%Y%m'
FACEBOOK_START_YEAR = 2004
FACEBOOK_START_MONTH = 2

DateTarget = namedtuple('DateTarget', ['as_string', 'as_date_time'])
Credentials = namedtuple('Credentials', ['email', 'password'])


def check_mount(my_month):
    """
    Makes sure given date conforms to a value that can be processed by the scraper.

    :param my_month: month parameter from sys.argv
    :return: my_month as a datetime object
    """
    if not my_month or len(my_month) != 6 or (
            # cause a more proper error message than strptime
            my_month[4] != '0' and my_month[4] != '1'):
        raise ValueError(my_month)

    year_month = datetime.strptime(my_month, MY_MONTH_FORMAT)
    # We actually need a timezone here around new year
    cur_year = datetime.now().year
    year = year_month.year
    if year < FACEBOOK_START_YEAR or year > cur_year:
        raise ValueError(f"Facebook data is not available for {year}")

    month = year_month.month
    if year == FACEBOOK_START_YEAR and month < FACEBOOK_START_MONTH:
        raise ValueError(f"Facebook data is not available for {my_month}")

    return year_month


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month",
                        help="Enter the year and month, for example, 202104")
    args = parser.parse_args()
    try:
        my_month = args.month
        year_month = check_mount(my_month)
    except ValueError as val_err:
        _logger.critical("Illegal month value: %s", val_err)
        return

    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    can_login = email and password
    if not can_login:
        _logger.warning("E-mail or password for scraper account is not set in ENV. "
                        "Accounts requiring login to access their data will not be scraped. "
                        "Consider setting EMAIL and PASSWORD env variables.")

    try:
        parse_urls(DateTarget(my_month, year_month), Credentials(email, password))
    except FileNotFoundError:
        _logger.critical("%s is missing, can not proceed.", URL_LIST_FILE_NAME)
        return


URL_LIST_FILE_NAME = "urls.lst"


def parse_urls(date_target, credentials):
    with open(Task.URL_HASH_CSV_PATH, "w", encoding="utf-8"):
        # just create or truncate
        pass

    public_scraper = PublicAccountScraper()
    try:
        with open(URL_LIST_FILE_NAME, "r", encoding="utf-8") as urls:
            for url in urls:
                url = url.strip("\n")
                if not url:
                    continue

                try:
                    # check if account is a public page
                    public_scraper.go_to(url)
                    scraper = public_scraper
                except PrivateAccountException:
                    _logger.error(
                        "%s requires private account parser. Not implemented yet. Ignoring...",
                        url)
                    # scraper = private_scraper
                    continue
                except TimeoutException:
                    _logger.error("Request to %s, timed out. Ignoring...", task.scraper.url)
                    continue
                except InvalidArgumentException:
                    _logger.error("Can not parse invalid url: (%s)", url)
                    continue

                task = Task(url, credentials, date_target, scraper)
                try:
                    task.run()
                except TemporarilyBannedException:
                    _logger.critical("Facebook might have banned us :(")
                    return
                except Exception as ex:
                    _logger.error("Unexpected error: (%s) %s", type(ex), ex)
    finally:
        public_scraper.close()


class Task:
    """ The task executed for each account """
    URL_HASH_CSV_PATH = Path("url-md5.csv")
    OCR_DIR = Path('OCR')
    DOM_DIR = Path('DOM')

    def __init__(self, url, credentials, date_target, scraper):
        self.account_url = url
        self.url_hash = md5(url.encode("utf-8")).hexdigest()
        self.credentials = credentials
        self.date_target = date_target
        self.scraper = scraper
        self.post_images = []
        self.post_counter = 0

    def account_screenshot_filename(self):
        """
        :return: file name to save the account page screenshot
        """
        return f"{APP_NAME}_{self.url_hash}.png"

    def all_posts_screenshot_filename(self):
        """
        :return: file name to save the screenshot containing all posts for date_target
        """
        return f"{APP_NAME}_{self.date_target.as_string}_{self.url_hash}.png"

    def dom_csv_path(self):
        """
        :return: csv filename to be placed under ./DOM
        """
        return self.DOM_DIR / f"{APP_NAME}_{self.url_hash}.csv"

    def save_url_hash(self):
        with open(self.URL_HASH_CSV_PATH, "a+", encoding="utf-8") as dom_out:
            writer = csv.writer(dom_out)
            writer.writerow([self.account_url, self.url_hash])

    def run(self):
        self.save_url_hash()
        self.scraper.full_page_screenshot(self.account_screenshot_filename())
        self.scraper.go_to_posts()
        self.scraper.scroll_down(self.date_target.as_date_time)
        self.OCR_DIR.mkdir(exist_ok=True)
        self.DOM_DIR.mkdir(exist_ok=True)
        # We don't want page wallpaper to block post content as we scroll down and screenshot
        self.scraper.wallpaper_visibility(False)
        self.scraper.filter_by(DateFilter(self.date_target.as_date_time),
                               PostConsumer(self.scraper, self))
        self.save_all_posts()

    def save_all_posts(self):
        """Assembles post screenshots into a single image and saves it"""
        src = [Image.open(BytesIO(img), formats=("PNG",)) for img in self.post_images]
        if src:
            width = src[0].width
            height = sum(img.height for img in src)
            dst = Image.new('RGB', (width, height))
            height_cursor = 0
            for img in src:
                dst.paste(img, (0, height_cursor))
                height_cursor += img.height
            dst.save(self.all_posts_screenshot_filename())

    def ocr_post_screenshot_path(self):
        """
        :return: a new file name for each post to be placed under ./OCR
        """
        self.post_counter += 1
        count = str(self.post_counter).zfill(4)
        return self.OCR_DIR / f"{APP_NAME}_{self.date_target.as_string}_{self.url_hash}_{count}.png"


class PostConsumer:
    """
    A consumer that acts on the parsed posts to save them in .csv and and save post screenshots
    """

    def __init__(self, scraper, task):
        self.scraper = scraper
        self.task = task

    def accept(self, parsed_post, post_element):
        with open(self.task.dom_csv_path(), "a+", encoding="utf-8") as dom_out:
            writer = csv.writer(dom_out)
            writer.writerow([parsed_post.likes, parsed_post.comments, parsed_post.shares])

        post_shot = self.scraper.element_screenshot_as_png(post_element)
        self.task.post_images.append(post_shot)

        self.scraper.post_reactions_screenshot(post_element,
                                               self.task.ocr_post_screenshot_path())

    def __call__(self, parsed_post, post_element):
        self.accept(parsed_post, post_element)


class DateFilter:
    """
        A predicate intended to be used for matching a Post's year and month
    """

    def __init__(self, year_month):
        """
            :param year_month:  a date-like object that has year and month attributes
        """
        self.year = year_month.year
        self.month = year_month.month

    def apply(self, post):
        return (self.year, self.month) == (post.time.year, post.time.month)

    def __call__(self, post):
        return self.apply(post)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()
