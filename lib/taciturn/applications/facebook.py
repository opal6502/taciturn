
# This file is part of the Taciturn web automation framework.
#
# Taciturn is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tactiurn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tactiurn.  If not, see <https://www.gnu.org/licenses/>.


from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from taciturn.applications.base import AppException
from taciturn.applications.login import LoginApplicationHandler

from time import sleep
import urllib.parse


class FacebookHandler(LoginApplicationHandler):
    application_name = 'facebook'

    application_url = "https://facebook.com"
    application_login_url = "https://facebook.com/login"

    def __init__(self, app_account, handler_stats=None, driver=None):
        super().__init__(app_account, handler_stats, driver)

    def login(self):
        login_wait = self.new_wait(timeout=10)
        self.driver.get(self.application_login_url)

        email_input_locator = (By.XPATH, '//input[@id="email"]')
        password_input_locator = (By.XPATH, '//input[@id="pass"]')
        login_button_locator = (By.XPATH, '//button[@id="loginbutton"]')

        login_wait.until(EC.element_to_be_clickable(email_input_locator))\
            .send_keys(self.app_username)
        login_wait.until(EC.element_to_be_clickable(password_input_locator))\
            .send_keys(self.app_password)
        login_wait.until(EC.element_to_be_clickable(login_button_locator))\
            .click()

        # check facebook icon to verify ...
        self._header_facebook_icon()

    def goto_homepage(self):
        self.driver.get(self.application_url)
        # self.e.header_facebook_icon().click()

    def goto_profile_page(self, user_name=None):
        if user_name:
            if self._is_facebook_id(user_name):
                self.driver.get(f'{self.application_url}/profile.php?id={user_name}')
            else:
                self.driver.get(f'{self.application_url}/{user_name}')
        else:
            self._header_profile_tab().click()
            self._header_profile_tab_profile().click()

    def _is_facebook_id(self, user_name):
        return len(user_name) == 20 and user_name.isnumeric()

    def _header_facebook_icon(self):
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]//a[@aria-label="Facebook"]')
        return self.new_wait().until(EC.visibility_of_element_located(locator))

    def _header_profile_tab(self):
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]//div[@aria-label="Account"]/img')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _header_profile_tab_profile(self):
        locator = (By.XPATH, '//div[@aria-label="Account" and @role="dialog"]'
                             '//span[@dir="auto" and text()="See your profile"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _page_header_overhang_y(self):
        header_element_locator = (By.XPATH, '//*[starts-with(@id,"mount")]/div/div/div[1]/div[3]/div/div'
                                            '/div[1]/div/div[2]/div/div/div[3]/div/div/div')
        header_element = self.new_wait().until(EC.presence_of_element_located(header_element_locator))
        self.element_scroll_to(header_element)
        return self.element_rect_bottom(header_element) + 60

    def _page_post_get_first(self):
        locator = (By.XPATH, '//div[@data-testid="Keycommand_wrapper_feed_story"]'
                             '/div[@data-testid="Keycommand_wrapper"]/div[@aria-posinset="1"]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _page_element_rescroll(self, page_element):
        self.driver.execute_script("window.scrollTo(0,0);")
        header_overhang_y = self._page_header_overhang_y()
        self.element_scroll_to(page_element, y_offset=header_overhang_y)

    def _page_post_get_link(self, page_post, retries=20):
        post_wait = self.new_wait(timeout=2)

        for try_n in range(1, retries+1):
            try:
                self._page_element_rescroll(page_post)

                # XXX I'm not sure if this is necessary Selnium/FB voodoo, try it first without:

                # post_date_locator = (By.XPATH, '(.//span[text()=" · "]/parent::span/parent::span'
                #                                '/preceding-sibling::span)[2]')
                # post_date_element = post_wait.until(EC.element_to_be_clickable(post_date_locator))
                # ActionChains(self.driver).move_to_element(post_date_element).perform()

                post_link_locator = (By.XPATH, '(.//span[text()=" · "]/parent::span/parent::span'
                                               '/preceding-sibling::span/span/a)[1]')
                post_link_element = post_wait.until(EC.presence_of_element_located(post_link_locator))

                post_link_href = post_link_element.get_attribute('href')
                return urllib.parse.urlparse(post_link_href).path
            except TimeoutException:
                pass

        raise AppException(f"Unable to scrape page post link after {retries} tries.")

    def _page_post_start_new(self, retries=20):
        post_wait = self.new_wait(timeout=2)

        for try_n in range(1, retries+1):
            try:
                new_post_button_locator = (By.XPATH, '//*[starts-with(@id,"mount")]//div[@aria-label="Create Post"]'
                                                     '//span[text()="Create Post"]')
                new_post_button_element = post_wait.until(EC.presence_of_element_located(new_post_button_locator))

                self._page_element_rescroll(new_post_button_element)

                new_post_button_element.click()

                return
            except (TimeoutException, ElementClickInterceptedException):
                pass

        raise AppException(f"Unable to start new page post after {retries} tries.")

    def _page_post_input(self):
        locator = (By.XPATH, '(//div[@role="dialog"])[1]//div[@role="textbox" and @contenteditable="true"] | '
                             '(//div[@role="dialog"])[2]//div[@role="textbox" and @contenteditable="true"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _page_post_wait_link_loading_invisible(self):
        # if the preview loading indicator is visible, give it some time:
        locator = (By.XPATH, '//*[@id="mount_0_0"]/div/div/div[1]/div[4]'
                             '//div[@data-visualcompletion="loading-state" and @role="progressbar"]')
        try:
            self.new_wait(timeout=90).until_not(EC.element_to_be_clickable(locator))
        except (NoSuchElementException, StaleElementReferenceException):
            pass

    def _page_post_wait_link_preview_xbutton_visible(self, retries=20):
        locator = (By.XPATH, '//div[@aria-label="Remove post attachment"]/i')
        return self.new_wait(timeout=90).until(EC.element_to_be_clickable(locator))

    def _page_post_submit_button(self):
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]//div[text()="Post"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _page_post_submit_new(self, post_body, post_link=None, retries=20):
        # do new post:
        for try_n in range(1, retries+1):
            try:
                self._page_post_start_new()
                post_input = self._page_post_input()

                # establish link preview:
                if post_link:
                    post_input.send_keys(post_link + ' ')

                    # wait for preview indicators:
                    # XXX DEBUG THIS CODE BEFORE SETTLING FOR A SLEEP:
                    # sleep(10)  # not desirable!!!
                    self._page_post_wait_link_loading_invisible()
                    self._page_post_wait_link_preview_xbutton_visible()

                    post_input.send_keys(Keys.COMMAND + 'a')
                    post_input.send_keys(Keys.BACKSPACE)

                post_input.send_keys(post_body)

                self._page_post_submit_button().click()

                return
            except (TimeoutException, ElementClickInterceptedException):
                self.driver.refresh()
                self.kill_javascript_alert()
                continue

        raise AppException(f"Couldn't submit new page post after {retries} tries.")

    def _page_post_verify_new(self, previous_first_post_link, retries=20):
        for try_n in range(1, retries+1):
            new_first_post = self._page_post_get_first()
            new_first_post_link = self._page_post_get_link(new_first_post)
            if new_first_post_link != previous_first_post_link:
                return new_first_post_link
            sleep(10)
            self.driver.refresh()

        raise AppException(f"New page post didn't show up after {retries} tries.")

    def page_post_create(self, page_path, post_body, post_link=None):
        self.goto_path(page_path)

        # scan first post:
        page_post_first = self._page_post_get_first()
        page_post_first_link = self._page_post_get_link(page_post_first)

        self._page_post_submit_new(post_body, post_link)
        return self._page_post_verify_new(page_post_first_link)




    # old methods:

    def pagepost_create(self, page_path, post_link, post_body):
        self.goto_path(page_path)
        sleep(10)
        admin_header_y = self.e.page_admin_overhang_bottom()

        # scan the first post ...
        first_post = self.e.page_post_first()
        self.element_scroll_to(first_post, y_offset=admin_header_y)

        first_post_link = self.e.page_post_link(first_post)
        print('pagepost_create: first_post_link =', first_post_link)

        # do our our post ...
        self.pagepost_esablish_link(page_path, post_link)
        create_post_input = self.e.page_post_input()
        print('pagepost_create: sending post body')
        # sleep(3)
        create_post_input.send_keys(post_body)
        print('pagepost_create: getting post submit button')
        # sleep(3)
        create_post_submit = self.e.page_post_submitbutton()
        create_post_submit.click()

        # now, wait for new post to show up on the page, verify and extract url ...
        # we're just going to try to wait until the first_post_link != new_first_link
        for try_n in range(1, self.default_load_retries+1):
            sleep(10)
            new_first_post = self.e.page_post_first()
            new_first_post_link = self.e.page_post_link(new_first_post)
            print("pagepost_create: '{}' != '{}'".format(new_first_post_link, first_post_link))
            if new_first_post_link != first_post_link:
                return self.application_url + new_first_post_link
            else:
                self.goto_page(page_path)
        else:
            raise RuntimeError("Couldn't verify new post identity")

    def pagepost_establish_link(self, page_path, link_url, retries=20):
        "puts the link in the create page input, makes sure the preview loads with image, then removes the link text."

        admin_header_y = self.e.page_admin_overhang_bottom()
        parsed_link = urllib.parse.urlparse(link_url)

        for try_n in range(1, retries+1):
            try:
                print("pagepost_esablish_link: getting page post elements ...")
                create_post_button = self.e.page_create_post_button()
                self.element_scroll_to(create_post_button, y_offset=admin_header_y)
                create_post_button.click()

                # insert link text to input ...
                print("pagepost_esablish_link: sending link text ...")
                create_post_input = self.e.page_post_input()
                create_post_input.send_keys(link_url+' ')

                print("pagepost_esablish_link: scanning for link preview image ({}) ...".format(parsed_link.netloc))
                preview_image = self.e.page_post_link_preview_image()
                if preview_image is not None:

                    #for n in range(len(link_url)+1):
                    #    create_post_input.send_keys(Keys.BACKSPACE)
                    sleep(10)
                    create_post_input.send_keys(Keys.COMMAND + 'a')
                    create_post_input.send_keys(Keys.BACKSPACE)

                    # take a look at this ajaxy input field ...
                    # create_post_input = self.e.page_post_input()
                    # with open('pagepost_esablish_link.html', 'w') as f:
                    #    f.write(create_post_input.get_attribute('innerHTML'))

                    return True
                else:
                    print('Couldn\'t get preview image!')
                    continue
            except (StaleElementReferenceException, NoSuchElementException, ElementClickInterceptedException) as e:
                print('pagepost_esablish_link: caught exception:', e)
                # sleep(5)
                if try_n == retries:
                    raise e
                print("pagepost_esablish_link, caught exception try {} of {}: {}".format(try_n, retries, e))
                self.goto_page(page_path)
                self.e.kill_alert()


class FacebookHandlerWebElements:
    implicit_default_wait = 60

    def __init__(self, driver):
        self.driver = driver

    def page_create_post_button(self, retries=10):
        for try_n in range(1, retries+1):
            try:  # following-sibling::div
                return self.driver.find_element(
                    By.XPATH,
                    '//*[starts-with(@id,"mount")]//div[@aria-label="Create Post"]//span[text()="Create Post"]')
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('page_create_post_button: caught exception:', e)
                # sleep(5)
                if try_n == retries:
                    raise e
                else:
                    print("page_create_post_button, caught exception try {} of {}: {}".format(try_n, retries, e))

    def page_create_post_header(self):
        # might not use this, but here it is anyway ...
        return self.driver.find_element(
            By.XPATH, '//*[starts-with(@id,"mount")]//form[@method="POST"]//h2[text()="Create Post"]')

    def page_post_input(self):
        # //div[starts-with(text(),"Write something")]
        # //div[starts-with(text(),"Write something")]/../..//div[@role="textbox" and @contenteditable="true"]
        # //div[@role="textbox" and @contenteditable="true"]/div[@data-contents="true"]/div[@data-block="true"]/div/span/br[@data-text="true"]
        # '(//div[@role="dialog"])[2]//div[@role="textbox" and @contenteditable="true"]'
        return self.driver.find_element(
            By.XPATH, '(//div[@role="dialog"])[1]//div[@role="textbox" and @contenteditable="true"] | '
                      '(//div[@role="dialog"])[2]//div[@role="textbox" and @contenteditable="true"]')
        # return self.driver.find_element(
        #     By.XPATH, '//div[starts-with(text(),"Write something")]/../..'
        #               '//div[@role="textbox" and @contenteditable="true"]')
        #               # '/div[@data-contents="true"]/div[@data-block="true"]/div/span/br[@data-text="true"]')

    def page_post_link_displaydomain(self):
        # displayed domain of link, like "foo.bar.com"
        # //*[@id="jsc_c_f0"]/div/div[1]/span/div
        # //*[starts-with(@id,"jsc_c")]/div/div[1]/span/div[text()="{domain}"]
        # pretty good area prefix:
        # //*[starts-with(@id,"jsc_c")]/div/div[1]/span/div[text()="anvilmesa.bandcamp.com"]/../..
        # or ...
        # //*[starts-with(@id,"jsc_c")]/div/div[1]/span/div[text()="anvilmesa.bandcamp.com"]/../../../../..
        return self.driver.find_element(
            By.XPATH, '//*[@id="jsc_c_f0"]/div/div[1]/span/div')

    def page_post_link_xbutton(self):
        # //div[@aria-label="Remove post attachment"]
        return self.driver.find_element(
            By.XPATH, '//div[@aria-label="Remove post attachment"]/i')

    def page_post_link_preview_image(self, retries=20):
        # html of post image in preview:
        # <img height="261" width="500" alt="Schlake Opus (track), by Anvil Mesa"
        # class="i09qtzwb n7fi1qx3 datstx6m pmk7jnqg j9ispegn kr520xx4 k4urcfbm bixrwtb6"
        # src="https://external-sjc3-1.xx.fbcdn.net/safe_image.php?d=AQBfQwheXGQueva7&amp;w=500&amp;h=261&amp;url=https%3A%2F%2Ff4.bcbits.com%2Fimg%2Fa2565667308_5.jpg&amp;cfs=1&amp;ext=jpg&amp;_nc_hash=AQDpLCIehhlWZpUG">
        # //*[@id="mount_0_0"]/div/div/div[1]/div[4]/div/div/div[1]/div/div[2]/div/div/div/form/div/div[1]/div/div[2]/div[2]/div[1]/div/div[2]/div/div[1]/div[1]/div/div/div/a/div[1]/div/div/div/img
        # the <a href=...> is going to contain our link's domain, we can see anchor our xpath on the href containing that
        # this seems pretty good:
        # //a[contains(@href, "{domain}")]//img
        for try_n in range(1, retries+1):
            try:
                self.driver.implicitly_wait(90)
                # check for the loading screen, and wait for it to pass
                # <div aria-busy="true" aria-valuemax="100" aria-valuemin="0" aria-valuetext="Loading..."
                # role="progressbar" tabindex="0" data-visualcompletion="loading-state"
                preview_loading = self.driver.find_element(
                    By.XPATH, '//*[@id="mount_0_0"]/div/div/div[1]/div[4]'
                              '//div[@data-visualcompletion="loading-state" and @role="progressbar"]')
                print('waiting for preview to load ...')
                WebDriverWait(self.driver, timeout=90).until(EC.invisibility_of_element(preview_loading))
                print('preview loaded.')
            except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
                pass
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

            try:  # following-sibling::div
                self.driver.implicitly_wait(0)

                print("page_post_link_image: scanning for image (x) button")
                img_xbox = self.driver.find_element(By.XPATH,
                                                    '//div[@aria-label="Remove post attachment"]/i')
                WebDriverWait(self.driver, timeout=90).until(EC.visibility_of(img_xbox))
                print("(x) is visible?")
                return True
            except (StaleElementReferenceException, NoSuchElementException) as e:
                # print('page_post_link_image: caught exception:', e)
                sleep(0.2)
                if try_n == retries:
                    raise e
                # else:
                #    print("page_post_link_image, caught exception try {} of {}: {}".format(try_n, retries, e))
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

    def page_post_submitbutton(self):
        return self.driver.find_element(By.XPATH, '//*[starts-with(@id,"mount")]//div[text()="Post"]')

    def page_post_first(self):
        # page post container:
        # //div[@data-testid="Keycommand_wrapper_feed_story"]/div[@data-testid="Keycommand_wrapper"]/div[@aria-posinset="10"]
        # XXX note this is 4 tags below actual post enclosing tag, but it's a good point of reference! (/../../../../)
        return self.driver.find_element(
            By.XPATH, '//div[@data-testid="Keycommand_wrapper_feed_story"]'
                      '/div[@data-testid="Keycommand_wrapper"]/div[@aria-posinset="1"]')

    def page_post_isfirstlinematch(self, page_post, post_body):
        "for quickly verifying the content of the post"
        page_element = page_post.find_element(By.XPATH, './/div/div/div/div/div/div[2]/div/div[3]'
                                                        '/div[1]/div/div/div/span/div[1]/div[1]')
        return page_element.text == post_body[:post_body.index('\n')]

    def page_post_link(self, page_post, retries=10):
        # get the link from a page post:
        # //*[@id="jsc_c_1k"]/span[2]/span/a
        # /html/body/div[1]/div/div/div[1]/div[3]/div/div/div[1]/div/div[2]/div/div/div[4]/div[2]/div/div[2]/div[3]/div/div/div[1]/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div/div[2]/div/div[2]/span/span/span[2]/span/a
        # ./div/div/div/div/div/div[2]/div/div[2]/div/div[2]/div/div[2]/span/span/span[2]/span/div/span
        # ./div/div/div/div/div/div[2]/div/div[2]/div/div[2]/div/div[2]/span/span/span[2]/span/a
        for try_n in range(1, retries+1):
            try:  # following-sibling::div
                self.driver.implicitly_wait(10)

                # strangely, we need to mouse over before the element becomes a proper link:
                mouseover_element = page_post.find_element(
                    By.XPATH,
                    '(.//span[text()=" · "]/parent::span/parent::span/preceding-sibling::span)[2]')
                print("page_post_link: Got mouse over element.")
                ActionChains(self.driver).move_to_element(mouseover_element).perform()

                link_element = page_post.find_element(
                    By.XPATH,
                    '(.//span[text()=" · "]/parent::span/parent::span/preceding-sibling::span/span/a)[1]')

                print('page_post_link: got element')
                attr_href = link_element.get_attribute('href')
                print('page_post_link: href =', attr_href)
                parsed_href_path = urllib.parse.urlparse(attr_href).path
                print('page_post_link: parsed href path =', parsed_href_path)

                return parsed_href_path
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('page_post_link: caught exception:', e)

                self.driver.execute_script("window.scrollTo(0,0);")
                offset = self.page_admin_overhang_bottom()
                self.driver.execute_script("arguments[0].scrollIntoView();", page_post)
                scroll_position = self.driver.execute_script("return document.documentElement.scrollTop;")
                self.driver.execute_script("window.scrollTo(0, arguments[0]);", scroll_position - (offset+60))

                if try_n == retries:
                    raise e
                else:
                    print("page_post_link, caught exception try {} of {}: {}".format(try_n, retries, e))
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

    def header_facebook_icon(self):
        return self.driver.find_element(
            By.XPATH, '//*[starts-with(@id,"mount")]/div/div/div[1]/div[2]/div[1]/a[@aria-label="Facebook"]')

    def header_profile_tab(self):
        return self.driver.find_element(
            By.XPATH, '//*[starts-with(@id,"mount")]'
                     '/div/div/div[1]/div[2]/div[4]/div[1]/span/div/'
                     'div[@aria-label="Account"]/img')

    def header_profile_tab_profile(self):
        # <div aria-label="Account" role="dialog" ...>
        # <span dir="auto" ...>See your profile</span>
        return self.driver.find_element(
            By.XPATH, '//div[@aria-label="Account" and @role="dialog"]'
                      '//span[@dir="auto" and text()="See your profile"]')

    def page_admin_overhang_bottom(self):
        # //*[starts-with(@id,"mount")]/div/div/div[1]/div[3]/div/div/div[1]/div/div[2]/div/div/div[3]
        # //*[starts-with(@id,"mount")]/div/div/div[1]/div[3]/div/div/div[1]/div/div[2]/div/div/div[3]
        e = self.driver.find_element(
            By.XPATH, '//*[starts-with(@id,"mount")]'
                      '/div/div/div[1]/div[3]/div/div/div[1]/div/div[2]/div/div/div[3]/div/div/div')
        self.driver.execute_script("arguments[0].scrollIntoView();", e)

        print("page_admin_overhang_bottom: got element.")

        offset_script = """
        var rect = arguments[0].getBoundingClientRect();
        return rect.bottom;
        """
        admin_header_bottom = self.driver.execute_script(offset_script, e)

        print("page_admin_overhang_bottom: admin_header_bottom =", admin_header_bottom)
        return int(admin_header_bottom)

    def kill_alert(self):
        try:
            WebDriverWait(self.driver, 3).until(EC.alert_is_present(),
                                            'Timed out waiting for PA creation ' +
                                            'confirmation popup to appear.')

            alert = self.driver.switch_to.alert
            alert.accept()
            print("kill_alert: alert accepted")
        except TimeoutException:
            print("kill_alert: no alert")
        finally:
            self.driver.switch_to.default_content()
