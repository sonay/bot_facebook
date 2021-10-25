import logging
from collections import namedtuple

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


_logger = logging.getLogger(__name__)

Post = namedtuple('Post', ['time', 'likes', 'comments', 'shares'])


def browser_with_fresh_profile(user_agent=None):
    """
    Creates a fresh Firefox Profile with accept-language HTTP header to retrieve pages in Turkish.
    :param user_agent: User Agent override, maybe used to fetch mobile pages because they are
                        somewhat easier to parse
    :return:    A Firefox profile
    """
    profile = FirefoxProfile()
    profile.set_preference("dom.webnotifications.enabled", False)
    profile.set_preference("app.update.enabled", False)
    profile.set_preference("intl.accept_languages", "tr-TR")
    if user_agent:
        profile.set_preference("general.useragent.override", user_agent)
    profile.update_preferences()
    options = Options()
    options.profile = profile
    driver = webdriver.Firefox(options=options, service_log_path=None)
    driver.maximize_window()
    return driver


class PrivateAccountException(Exception):
    """ Raised to signal account page is not public """


class PublicAccountScraper:
    """
        A parser that operates on public Facebook accounts using a Selenium-driven Firefox instance.
    """

    # The login form when Facebook wants user to login in page content,
    # not the fixed header
    LOGIN_FORM_XPATH = "//div[@id='globalContainer']" \
                       "//form[@id='login_form']"

    # "Posts" link in the sidebar for public pages
    SIDEBAR_POSTS_LINK_XPATH = "//div[@id='entity_sidebar']" \
                               "//div" \
                               "//a" \
                               "/span[text()='Gönderiler']" \
                               "/parent::a"

    # Annoying sticky banner to encourage membership
    PAGELET_XPATH = "//div[@id='pagelet_growth_expanding_cta']"

    def __init__(self, browser=None):
        self.browser = browser if browser else browser_with_fresh_profile()
        self.url = ""

    def go_to(self, url):
        self.browser.get(url)
        self.url = url
        self.check_privacy()

    def check_privacy(self):
        if self._requires_login():
            _logger.debug("Page requires login, bailing out.")
            raise PrivateAccountException(f"Need login to parse: {self.url}")

    def _requires_login(self):
        try:
            login_form = self.browser.find_element(By.XPATH, self.LOGIN_FORM_XPATH)
        except NoSuchElementException:
            pass
        else:
            if login_form.is_displayed():
                return True
        try:
            # Account might not be a public page. For example a private account with some public
            # info would still not be parsable by this parser.
            self.browser.find_element(By.XPATH, self.SIDEBAR_POSTS_LINK_XPATH)
        except NoSuchElementException:
            return True
        else:
            return False

    def close(self):
        self.browser.close()

    def full_page_screenshot(self, file_path):
        """
            Takes a full page screenshot and saves in file_path
            :param file_path: path to save file, relative to current working directory
        """
        self._delete_view_blocking_elements()
        self.browser.get_full_page_screenshot_as_file(str(file_path))

    def _delete_view_blocking_elements(self):
        self._delete_pagelet_banner()

    def _delete_pagelet_banner(self):
        try:
            banner = self.browser.find_element(By.XPATH, self.PAGELET_XPATH)
            self._remove_element(banner)
        except NoSuchElementException:
            pass

    def _remove_element(self, element):
        self.browser.execute_script(
            """
                var elem = arguments[0]
                elem.parentNode.removeChild(elem)
            """, element)

