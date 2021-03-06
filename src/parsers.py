import logging
import random
import time
from collections import namedtuple
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from exceptions import PrivateAccountException, TemporarilyBannedException
from utils import xpath_endswith

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
                               "/span[text()='G??nderiler']" \
                               "/parent::a"

    # Annoying sticky banner to encourage membership
    PAGELET_XPATH = "//div[@id='pagelet_growth_expanding_cta']"

    # A spinbox Facebook uses while loading elements on a page
    PROGRESSBAR_XPATH = "//div[@id='www_pages_reaction_see_more_unitwww_pages_posts']" \
                        "//span[contains(@class, 'uiMorePagerLoader')]" \
                        "/span"

    # A post is wrapped in a userContentWrapper
    # Has a header-like div that contains the time
    POST_XPATH = "//div[@id='globalContainer']" \
                 "//div[@id='content_container']" \
                 "//div[@id='pagelet_timeline_main_column']" \
                 "//div[contains(@class, 'userContentWrapper')]"

    # Use on a post element.
    # attributes:
    #   data-utime: has date as a timestamp
    #   data-tooltip-content: has localized date in long form
    #   data-shorten: customizes how date is represented in UI
    POST_TIME_XPATH = ".//div[starts-with(@id, 'feed_subtitle')]//abbr"

    POST_DATE_ATTRIBUTE = "data-tooltip-content"

    POST_DATE_FORMAT = '%d %B %Y %A, %H:%M'

    # Reaction Box is a form element in a Facebook post wrapper
    # that contains like, comment, share counts, buttons for those
    # and comments area where user can input their comments.
    REACTION_BOX_XPATH = ".//form[@class='commentable_item']"

    # Use on a reaction box
    # To remove reaction icons to help tesseract
    LIKES_ICON_XPATH = ".//span[@aria-label='Buna ifade b??rakanlar?? g??r']"

    # Use on a reaction box
    # To remove icons from reaction buttons
    REACTION_BOX_BUTTONS_XPATH = ".//i[@data-visualcompletion='css-img']"

    # Use on a post element.
    # Text of the selected element is the number of likes.
    # Selects at most two elements, both give the same number
    # of likes as seen on the user interface
    LIKES_XPATH = ".//a[@data-testid='UFI2ReactionsCount/root']" \
                  "/span" \
                  "/span[@data-hover='tooltip']" \
                  "/span"

    # Use on a post element
    # Text of the selected element is the number of comments.
    # For example:
    #   4 Yorum
    COMMENTS_XPATH = ".//form[@class='commentable_item']" \
                     "//span" \
                     f"/a[{xpath_endswith('text()', 'Yorum')}]"

    # Use on a post element
    # Text of the selected element is the number of shares.
    # For example:
    #   1 Payla????m
    SHARES_XPATH = ".//form[@class='commentable_item']" \
                   f"//span[{xpath_endswith('text()', 'Payla????m')}]"

    # Remove this to create more space for post screenshots
    # It overlaps the post time on small screens.
    FLOATING_REACTION_BOX_XPATH = "//div[contains(@class, 'fixed_elem')]"

    # Use on a reaction box
    # To remove comments to help tesseract
    COMMENTS_HEADER_XPATH = ".//h6[@class='accessible_elem' and text()='Yorumlar']/parent::div"

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

    def go_to_posts(self):
        posts_link = self.browser.find_element(By.XPATH, self.SIDEBAR_POSTS_LINK_XPATH)
        self.go_to(posts_link.get_attribute('href'))

    def scroll_down(self, date_target):
        """
        Scroll down until we hit just before our target month.
        Going too far down, say for six months, might get us blocked/banned.
        """
        last_post = None
        while True:
            self._do_scroll()
            WebDriverWait(self.browser, timeout=30) \
                .until(
                EC.invisibility_of_element_located(
                    (By.XPATH, self.PROGRESSBAR_XPATH)))
            if self._requires_login():
                raise TemporarilyBannedException()

            lp_element = self.browser.find_element(By.XPATH,
                                                   f"({self.POST_XPATH})[last()]")
            try:
                lp = self._parse_post(lp_element)
            except Exception as ex:
                _logger.error("%s: innerHTML:%s", ex, lp_element.get_attribute("innerHTML"))
                raise ex from None

            if lp.time < date_target:
                # we past the target month
                _logger.info("Passed target with %s", date_target)
                break

            # We hit bottom, no more posts
            if last_post == lp:
                break
            last_post = lp

    def _do_scroll(self, ):
        # sometimes one scroll is not enough, for some reason
        for _ in range(2):
            self.browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.randint(3, 7))

    def _parse_post(self, post_element):
        post_time = post_element.find_element(
            By.XPATH, self.POST_TIME_XPATH).get_attribute(self.POST_DATE_ATTRIBUTE)
        post_time = datetime.strptime(post_time, self.POST_DATE_FORMAT)
        likes = self._reaction_count(post_element, self.LIKES_XPATH)
        comments = self._reaction_count(post_element, self.COMMENTS_XPATH)
        shares = self._reaction_count(post_element, self.SHARES_XPATH)
        return Post(post_time, likes, comments, shares)

    @staticmethod
    def _reaction_count(post_element, xpath):
        try:
            element = post_element.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            return 0
        return int(element.text.split(maxsplit=1)[0])

    def filter_by(self, predicate, consumer):
        """
        :param predicate: A predicate function that takes a Post as input.

        :param consumer: A callback function to be called with parsed post and post element
                         matching the predicate.
        """
        post_elements = self.browser.find_elements(By.XPATH, self.POST_XPATH)
        for post_element in post_elements:
            post = self._parse_post(post_element)
            if predicate(post):
                consumer(post, post_element)

    def element_screenshot_as_png(self, element):
        self._delete_view_blocking_elements()
        self._move_to_element(element)
        return element.screenshot_as_png

    def _move_to_element(self, element):
        # WORK AROUND
        # Firefox driver does not move to element if not in viewport
        # because they believe there should be a scroll standard
        # see: https://github.com/mozilla/geckodriver/issues/776
        self.browser.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(0.01)
        ActionChains(self.browser).move_to_element(element).perform()
        time.sleep(0.01)

    def wallpaper_visibility(self, visible):
        try:
            box = self.browser.find_element(By.XPATH, self.FLOATING_REACTION_BOX_XPATH)
            visibility = 'visible' if visible else 'hidden'
            self.browser.execute_script(
                f"""
                    var wallpaper = arguments[0]
                    wallpaper.style.visibility = '{visibility}'
                """, box)
        except NoSuchElementException:
            pass

    def post_reactions_screenshot(self, post_element, file_path):
        """
            Takes a screenshot of the given element after moving to it.
            :param post_element: the dom element for the post
            :param file_path: path to save file, relative to current working directory
        """
        self._delete_view_blocking_elements()
        try:
            reaction_box = post_element.find_element(By.XPATH, self.REACTION_BOX_XPATH)
            self._safe_clean_reaction_box(reaction_box)
        except NoSuchElementException:
            reaction_box = post_element
        self._move_to_element(reaction_box)
        reaction_box.screenshot(str(file_path))

    def _safe_clean_reaction_box(self, reaction_box):
        self._safe_remove_element(reaction_box, self.COMMENTS_HEADER_XPATH)
        self._safe_remove_element(reaction_box, self.LIKES_ICON_XPATH)
        # Three times (Like, Comment, Share)
        self._safe_remove_element(reaction_box, self.REACTION_BOX_BUTTONS_XPATH)
        self._safe_remove_element(reaction_box, self.REACTION_BOX_BUTTONS_XPATH)
        self._safe_remove_element(reaction_box, self.REACTION_BOX_BUTTONS_XPATH)

    def _safe_remove_element(self, ancestor, xpath):
        try:
            element = ancestor.find_element(By.XPATH, xpath)
            self._remove_element(element)
        except NoSuchElementException:
            pass


class PrivateAccountScraper:
    FACEBOOK_HOME_URL = "https://www.facebook.com"

    def __init__(self, credentials, browser=None):
        self.credentials = credentials
        self.logged_in = False
        self.browser = browser if browser else browser_with_fresh_profile()

    def login(self):
        if self.logged_in:
            return
        self.browser.get(self.FACEBOOK_HOME_URL)
        self.browser.find_element(By.NAME, 'email').send_keys(self.credentials.email)
        self.browser.find_element(By.NAME, 'pass').send_keys(self.credentials.password)
        self.browser.find_element(By.NAME, 'login').click()
        self.logged_in = True

    def full_page_screenshot(self, file_path):
        time.sleep(3)
        self.browser.get_full_page_screenshot_as_file(str(file_path))

    def go_to(self, url):
        self.login()
        self.browser.get(url)

    def go_to_posts(self):
        """NO-OP. We should already be at posts at all times."""

    def scroll_down(self, date_target):
        """Click on filter, choose date_target."""

    def wallpaper_visibility(self, visible):
        """NO-OP wallpaper doesn't overlay posts when logged-in"""

    def filter_by(self, predicate, consumer):
        """Parse posts, apply by predicate, supply to consumer."""

    def close(self):
        self.browser.close()
