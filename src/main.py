import csv
import logging
import os
import sys
import argparse
from collections import namedtuple
from datetime import datetime
from hashlib import md5
from pathlib import Path

from selenium.common.exceptions import TimeoutException, InvalidArgumentException

from parsers import PublicAccountScraper, PrivateAccountException

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
                except Exception as ex:
                    _logger.error("Unexpected error: (%s) %s", type(ex), ex)
    finally:
        public_scraper.close()


class Task:
    """ The task executed for each account """
    URL_HASH_CSV_PATH = Path("url-md5.csv")

    def __init__(self, url, credentials, date_target, scraper):
        self.account_url = url
        self.url_hash = md5(url.encode("utf-8")).hexdigest()
        self.credentials = credentials
        self.date_target = date_target
        self.scraper = scraper

    def account_screenshot_filename(self):
        """
        :return: file name to save the account page screenshot
        """
        return f"{APP_NAME}_{self.url_hash}.png"

    def save_url_hash(self):
        with open(self.URL_HASH_CSV_PATH, "a+", encoding="utf-8") as dom_out:
            writer = csv.writer(dom_out)
            writer.writerow([self.account_url, self.url_hash])

    def run(self):
        self.save_url_hash()
        self.scraper.full_page_screenshot(self.account_screenshot_filename())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()
