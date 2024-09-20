from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
from tabulate import tabulate
import time
from concurrent.futures import ThreadPoolExecutor
from hiveengine import tokenobject
import itertools
import requests
import argparse
import sys

from chromedriver_update import update_driver


# List accounts to check, priority given to command line arguments if provided
manual_override = []

# Default accounts, used if manual_override is empty and no command line args given
accounts = [
    "mythic534",
    "mythic535",
    "mythic536",
    "mythic537",
    "mythic539"
]


def main():

    global accounts
    update_driver()
    start_time = time.time()

    if len(sys.argv) > 1:
        accounts = parse_arguments()

    elif len(manual_override) > 0:
        accounts = manual_override

    with ThreadPoolExecutor(max_workers=len(accounts)) as executor:
        cards_data = list(executor.map(get_cards, accounts))

    SPS_price, DEC_price = get_tokens_price()

    with ThreadPoolExecutor(max_workers=len(accounts)) as executor:
        tokens_data = list(executor.map(get_tokens, accounts, itertools.repeat(SPS_price), itertools.repeat(DEC_price)))

    results = combine_lists(cards_data, tokens_data, 'Account')

    print_dict(results)

    end_time = time.time()
    total_runtime = end_time - start_time

    print(f"Total runtime: {total_runtime:.2f} seconds\n")


def parse_arguments():
    "Parse command line arguments, if provided"

    parser = argparse.ArgumentParser(description="Quick valuation of Splinterlands accounts")
    parser.add_argument('-a', '--accounts', nargs='+', help='List of accounts to check')
    args = parser.parse_args()

    if args.accounts:
        return args.accounts

    return []


def get_cards(account):

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ensure GUI is off
    chrome_options.add_argument("--log-level=3")  # Ignore random logging info

    driver = webdriver.Chrome(options=chrome_options)
    url = f"https://peakmonsters.com/@{account}/cards"
    driver.get(url)

    cards_value = search_loop(account, driver)

    driver.quit()
    return {'Account': account, 'Cards /$': cards_value}


def search_loop(account, driver):
    "Iterate until a non-zero value is returned by peakmonsters, then return value"

    i = 0
    while i < 100:
        
        time.sleep(0.2)
        
        try:
            itemlist = driver.find_elements(By.CLASS_NAME, "text-semibold")
            cards_value_formatted = itemlist[8].text

            cards_value = float(cards_value_formatted.replace('$', '').replace(',', '').strip())

            if cards_value:
                print(f"{account} cards value: {cards_value:.2f}")
                return(cards_value)
            
            else:
                i += 1

        except:
            i += 1

    return(0)


def get_tokens_price():
    "Returns SPS price, DEC price"

    SPS_HIVE = float(tokenobject.Token("SPS").get_market_info()['lastPrice'])
    DEC_HIVE = float(tokenobject.Token("DEC").get_market_info()['lastPrice'])
    USD_HIVE = float(tokenobject.Token("SWAP.HBD").get_market_info()['lastPrice'])

    SPS_USD = SPS_HIVE/USD_HIVE

    DEC_USD = DEC_HIVE/USD_HIVE

    print(f"\nSPS price: {SPS_USD:.6f}")
    print(f"DEC price: {DEC_USD:.6f}\n")

    return SPS_USD, DEC_USD


def get_tokens(account, SPS_price, DEC_price):

    response = requests.get(f"https://api.splinterlands.com/players/balances?username={account}")
    data = response.json()

    SPS = 0
    DEC = 0
    for item in data:

        if item['token'] == "SPSP":
            SPS += item['balance']
        
        elif item['token'] == "SPS":
            SPS += item['balance']

        elif item['token'] == "DEC":
            DEC += item['balance']

    if DEC:
        print(f"{account} DEC: {DEC:.2f}")

    if SPS:
        print(f"{account} SPS: {SPS:.2f}")

    return{'Account': account, 'SPS /$': SPS * SPS_price, 'DEC /$': DEC * DEC_price}


def combine_lists(list1, list2, key):
    "Combine lists of dicts with a common key"

    combined = {}

    for item in list1:
        combined[item[key]] = item

    for item in list2:
        if item[key] in combined:
            combined[item[key]].update(item)
        else:
            combined[item[key]] = item

    return list(combined.values())


def print_dict(_dict):
    "Pretty prints a list of dicts to stdout"
    
    df = pd.DataFrame.from_dict(_dict)
    
    df['Cards /$'] = df['Cards /$'].astype(float)
    df['SPS /$'] = df['SPS /$'].astype(float)
    df['DEC /$'] = df['DEC /$'].astype(float)
    
    df['Total /$'] = df['Cards /$'] + df['SPS /$'] + df['DEC /$']

    df['Cards /$'] = df['Cards /$'].map('{:.2f}'.format)
    df['SPS /$'] = df['SPS /$'].map('{:.2f}'.format)
    df['DEC /$'] = df['DEC /$'].map('{:.2f}'.format)
    df['Total /$'] = df['Total /$'].map('{:.2f}'.format)
    
    cards_sum = df['Cards /$'].astype(float).sum()
    SPS_sum = df['SPS /$'].astype(float).sum()
    DEC_sum = df['DEC /$'].astype(float).sum()
    total_sum = df['Total /$'].astype(float).sum()
    
    df.replace('0.00', '-', inplace=True)
    
    sum_row = pd.DataFrame({'Account': ['Total'], 'Cards /$': [f"{cards_sum:.2f}"], 'SPS /$': [f"{SPS_sum:.2f}"], 'DEC /$': [f"{DEC_sum:.2f}"], 'Total /$': [f"{total_sum:.2f}"]})
    space_row = pd.DataFrame({'Account': ['---------'], 'Cards /$': ['---------'], 'SPS /$': ['--------'], 'DEC /$': ['--------'], 'Total /$': ['---------']})
    df = pd.concat([df, space_row, sum_row], ignore_index=True)

    table = tabulate(df, showindex="False", headers='keys', tablefmt='psql', floatfmt=".2f", colalign=("center", "right", "right", "right", "right"))
    
    print(f"\n{table}\n")


if __name__ == "__main__":
    main()