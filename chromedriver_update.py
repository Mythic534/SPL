from webdriver_auto_update.chrome_app_utils import ChromeAppUtils
from webdriver_auto_update.webdriver_manager import WebDriverManager


def update_driver():

    print()
    # Using ChromeAppUtils to inspect Chrome application version
    chrome_app_utils = ChromeAppUtils()
    chrome_app_version = chrome_app_utils.get_chrome_version()
    print("Chrome application version:", chrome_app_version)

    # Target directory to store chromedriver
    driver_directory = ""

    # Create an instance of WebDriverManager
    driver_manager = WebDriverManager(driver_directory)

    # Call the main method to manage chromedriver
    driver_manager.main()
    print()


if __name__ == "__main__":
    update_driver()