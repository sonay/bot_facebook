import logging
import os
import sys
import argparse
from collections import namedtuple
from datetime import datetime

_logger = logging.getLogger(__name__)

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
    with open(URL_LIST_FILE_NAME, "r", encoding="utf-8") as urls:
        for url in urls:
            url = url.strip("\n")
            if not url:
                continue


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()
