import logging.handlers

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import socket
import datetime
from utils import *

TIME_OUT_ELEMENT = 60
TIME_OUT_VIDEO = 10


class Moodle:

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        s = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=s, options=options)
        self.connect()

    def connect(self):
        logging.info('connect Moodle')
        try_driver(lambda: self.driver.get('https://lemida.biu.ac.il/'))
        WebDriverWait(self.driver, TIME_OUT_ELEMENT).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="pre-login-form"]/button'))).click()
        WebDriverWait(self.driver, TIME_OUT_ELEMENT).until(
            EC.presence_of_element_located((By.ID, 'login_username'))).send_keys(
            open('id.txt', 'r').readline())
        WebDriverWait(self.driver, TIME_OUT_ELEMENT).until(
            EC.presence_of_element_located((By.ID, 'login_password'))).send_keys(
            open('pass.txt', 'r').readline())
        WebDriverWait(self.driver, TIME_OUT_ELEMENT).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="login"]/div/div[4]/input[1]'))).click()

    def work(self):
        last_time_alive = datetime.datetime.now()
        exceptions = 0
        while True:
            try:
                logging.info('work loop')
                WebDriverWait(self.driver, TIME_OUT_ELEMENT).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="frontpage-course-list"]/div')))
                courses_links = self.get_courses_links()
                for link in courses_links:
                    self.save_course(link)
                now = datetime.datetime.now()
                delta = now - last_time_alive
                if delta.seconds > 60 * 60 * 3:
                    logging.info('notify admin server still alive')
                    last_time_alive = now
                    send_email('server is alive', f'{now}\n{socket.gethostname()}', Admin_Email)
                logging.info('wait 3 minutes')
                time.sleep(3 * 60)
            except Exception as exception1:
                exceptions += 1
                logging.exception('exception in work loop')
                try:
                    logging.info('try to connect again')
                    self.connect()
                except Exception as exception2:
                    logging.exception('connecting again failed')
                    if exceptions > 2:
                        logging.exception('more then 2 tries to connect again, raise exception')
                        raise exception2

    def save_course(self, course_link):
        logging.info('get course page')
        try_driver(lambda: self.driver.get(course_link))
        WebDriverWait(self.driver, TIME_OUT_ELEMENT).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="page-navbar"]/nav/ol/li[2]/span/a')))
        course_num = self.driver.find_element(By.XPATH, '//*[@id="page-navbar"]/nav/ol/li[2]/span/a').get_attribute(
            'title')
        course_name = self.driver.find_element(By.XPATH, '//*[@id="page-navbar"]/nav/ol/li[2]/span/a/span').text
        logging.info(f'save course: {course_num} - {course_name}')
        WebDriverWait(self.driver, TIME_OUT_ELEMENT).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="region-main"]/div/div/ul')))
        topics = list()
        topics.extend(self.find_zoom_videos())
        elements = self.driver.find_elements(By.CLASS_NAME, 'instancename')
        for element in elements:
            try:
                topics.append(element.text.replace('\n', ':'))
            except:
                topics.append(element.text)
        course_file_path = Path(os.path.join(os.getcwd(), 'elements', f'{course_num}.txt'))
        if not course_file_path.is_file():
            logging.info(f'new course: {course_num} - {course_name}')
            new_course(course_file_path, topics)
        else:
            is_changed(course_name, course_file_path, topics)
        logging.info('go back')
        try_driver(lambda: self.driver.get('https://lemida.biu.ac.il/'))

    def get_courses_links(self):
        course_list = list()
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828955001').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828922602').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828922603').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828923101').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828923103').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828958103').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828958104').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828936208').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828936201').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828921106').get_attribute('href'))
        course_list.append(
            self.driver.find_element(By.PARTIAL_LINK_TEXT, '828921101').get_attribute('href'))
        return course_list

    def find_zoom_videos(self):
        zoom_topics = list()
        try:
            logging.info('wait for videos')
            WebDriverWait(self.driver, TIME_OUT_VIDEO).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="zoomvideos"]/div')))
        except Exception:
            logging.exception('no videos in this course')
            return zoom_topics
        i = 1
        while True:
            try:
                zoom_topics.append(self.driver.find_element(By.XPATH,
                                                            f'/html/body/div[6]/div[1]/div[2]/aside/div[1]/div[2]/div[2]/div[3]/div/div/div[2]/div[{i}]/div[3]/a').get_attribute(
                    'title'))
                logging.info(f'found {i} video')
                i += 1
            except Exception:
                logging.exception(f'video {i} not found')
                break
        return zoom_topics


if __name__ == '__main__':
    handler = logging.handlers.RotatingFileHandler('logger.log', 'a', 20000000, 5)
    logging.basicConfig(handlers=[handler], level=logging.INFO,
                        format='%(levelname)s : %(message)s : %(asctime)s\n')
    logging.info('start')
    while True:
        try:
            logging.info('main loop')
            moodle = Moodle()
            moodle.work()
        except Exception as exception:
            logging.exception('exception in main loop')
            try:
                logging.info('try to send email to admin')
                send_email('error - program crushed!', f'{datetime.datetime.now()}\n{socket.gethostname()}',
                           Admin_Email, Path('logger.log'))
            except Exception:
                logging.exception('failed to send email to admin')
