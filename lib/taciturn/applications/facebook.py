
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
    UnexpectedAlertPresentException
)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from taciturn.applications.base import (
    BaseApplicationHandler,
    ApplicationWebElements,
    AppDataAnchorMissingException
)

from time import sleep
import urllib.parse


class FacebookHandler(BaseApplicationHandler):
    application_name = 'facebook'

    application_url = "https://facebook.com"
    application_login_url = "https://facebook.com/login"

    implicit_default_wait = 60

    def __init__(self, options, db_session, app_account, elements=None):
        super().__init__(options, db_session, app_account, FacebookHandlerWebElements)

        self.follow_back_hiatus = self.config['app:twitter']['follow_back_hiatus']
        self.unfollow_hiatus = self.config['app:twitter']['unfollow_hiatus']
        self.action_timeout = self.config['app:twitter']['action_timeout']
        self.mutual_expire_hiatus = self.config['app:twitter']['mutual_expire_hiatus']

        self.init_webdriver()

        self.goto_homepage()

    def login(self):
        self.driver.get(self.application_login_url)

        email_field = self.driver.find_element(By.XPATH, '//input[@id="email"]')
        email_field.send_keys(self.app_username)

        password_field = self.driver.find_element(By.XPATH, '//input[@id="pass"]')
        password_field.send_keys(self.app_password)

        login_button = self.driver.find_element(By.XPATH, '//button[@id="loginbutton"]')
        login_button.click()

        # check facebook icon to verify ...
        self.e.header_facebook_icon()

    def goto_homepage(self):
        self.driver.get(self.application_url)
        # self.e.header_facebook_icon().click()

    def goto_user_page(self):
        self.e.header_profile_tab().click()
        self.e.header_profile_tab_profile().click()

    def goto_page(self, page_path):
        self.driver.get(self.application_url+'/'+page_path)

    def pagepost_create(self, page_path, post_link, post_body):
        self.goto_page(page_path)
        admin_header_y = self.e.page_admin_overhang_bottom()

        # scan the first post ...
        first_post = self.e.page_post_first()
        self.scrollto_element(first_post, offset=admin_header_y)

        with open('fb_page_post.html', 'w') as f:
            f.write(first_post.get_attribute('innerHTML'))

        first_post_link = self.e.page_post_link(first_post)
        print('pagepost_create: first_post_link =', first_post_link)

        # do our our post ...
        self.pagepost_esablish_link(page_path, post_link)
        create_post_input = self.e.page_post_input()
        print('pagepost_create: sending post body')
        sleep(3)
        create_post_input.send_keys(post_body)
        print('pagepost_create: getting post submit button')
        sleep(3)
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
                return new_first_post_link
            else:
                self.goto_page(page_path)
        else:
            raise AppDataAnchorMissingException("Couldn't verify new post identity")

    def pagepost_esablish_link(self, page_path, link_url, retries=10):
        "puts the link in the create page input, makes sure the preview loads with image, then removes the link text."
        self.goto_page(page_path)
        admin_header_y = self.e.page_admin_overhang_bottom()

        parsed_link = urllib.parse.urlparse(link_url)

        for try_n in range(1, retries+1):
            try:
                print("pagepost_esablish_link: getting page post elements ...")
                create_post_button = self.e.page_create_post_button()
                self.scrollto_element(create_post_button, offset=admin_header_y)
                create_post_button.click()

                # insert link text to input ...
                print("pagepost_esablish_link: sending link text ...")
                create_post_input = self.e.page_post_input()
                create_post_input.send_keys(link_url+' ')
                # create_post_input.send_keys(Keys.SHIFT + Keys.ENTER)

                print("pagepost_esablish_link: scanning for link preview image ...")
                preview_image = self.e.page_post_link_image(parsed_link.netloc)
                if preview_image is not None:
                    print("Got preview image!")

                    create_post_input.send_keys(Keys.COMMAND + "A")
                    create_post_input.send_keys(Keys.DELETE)

                    return True

            except ( #UnexpectedAlertPresentException,
                    StaleElementReferenceException,
                    NoSuchElementException,
                    TimeoutException) as e:
                print('pagepost_esablish_link: caught exception:', e)
                sleep(0.2)
                if try_n == retries:
                    raise e
                else:
                    # try reloading the page and trying again ...
                    print("pagepost_esablish_link, caught exception try {} of {}: {}".format(try_n, retries, e))
                    self.goto_page(page_path)
                    self.e.kill_alert()


class FacebookHandlerWebElements(ApplicationWebElements):
    implicit_default_wait = 60

    def page_create_post_button(self):
        return self.driver.find_element(
            By.XPATH, '//*[starts-with(@id,"mount")]//div[@aria-label="Create Post"]//span[text()="Create Post"]')

    def page_create_post_header(self):
        # might not use this, but here it is anyway ...
        return self.driver.find_element(
            By.XPATH, '//*[starts-with(@id,"mount")]//form[@method="POST"]//h2[text()="Create Post"]')

    def page_post_input(self):
        # //div[starts-with(text(),"Write something")]
        # //div[starts-with(text(),"Write something")]/../..//div[@role="textbox" and @contenteditable="true"]
        # //div[@role="textbox" and @contenteditable="true"]/div[@data-contents="true"]/div[@data-block="true"]/div/span/br[@data-text="true"]
        return self.driver.find_element(
            By.XPATH, '//div[starts-with(text(),"Write something")]/../..'
                      '//div[@role="textbox" and @contenteditable="true"]'
                      '/div[@data-contents="true"]/div[@data-block="true"]/div/span/br[@data-text="true"]')

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

    def page_post_link_image(self, link_domain, retries=10):
        # html of post image in preview:
        # <img height="261" width="500" alt="Schlake Opus (track), by Anvil Mesa"
        # class="i09qtzwb n7fi1qx3 datstx6m pmk7jnqg j9ispegn kr520xx4 k4urcfbm bixrwtb6"
        # src="https://external-sjc3-1.xx.fbcdn.net/safe_image.php?d=AQBfQwheXGQueva7&amp;w=500&amp;h=261&amp;url=https%3A%2F%2Ff4.bcbits.com%2Fimg%2Fa2565667308_5.jpg&amp;cfs=1&amp;ext=jpg&amp;_nc_hash=AQDpLCIehhlWZpUG">
        # //*[@id="mount_0_0"]/div/div/div[1]/div[4]/div/div/div[1]/div/div[2]/div/div/div/form/div/div[1]/div/div[2]/div[2]/div[1]/div/div[2]/div/div[1]/div[1]/div/div/div/a/div[1]/div/div/div/img
        # the <a href=...> is going to contain our link's domain, we can see anchor our xpath on the href containing that
        # this seems pretty good:
        # //a[contains(@href, "{domain}")]//img
        for try_n in range(1, retries+1):
            try:  # following-sibling::div
                self.driver.implicitly_wait(0)
                print("page_post_link_image: scanning for image with domain '{}'".format(link_domain))
                img_element = self.driver.find_element(By.XPATH, '//a[contains(@href,"{}")]//img'.format(link_domain))
                print("page_post_link_image: img_element =", img_element)
                return img_element
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('page_post_link_image: caught exception:', e)
                # sleep(5)
                if try_n == retries:
                    raise e
                else:
                    print("page_post_link_image, caught exception try {} of {}: {}".format(try_n, retries, e))
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