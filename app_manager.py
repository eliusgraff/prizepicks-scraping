import os
import web_scraper
import my_parser
from prizepicks_db import send_to_sql
import my_logs
import datetime
import time

def save_wp_data(wp, fn):
    '''
    Function to take data from PrizePicks API and save it as a file.
    It takes 2 arguments:
        wp - wbpage data to be saved
        fn - name of file to save the webpage data at
    '''
    with open(fn, 'w', encoding='utf-8') as file:
        file.write(wp)

    print(f"Wrote WP to: {fn}")

def get_wp_example(fn = None):
    '''
    Function to load in example file for development use or request a new one from the prizepicks API.
    '''

    if fn is None:
        fn = "test files\\NBAtest.txt"

    '''
    This line checks to see if there is an existing file that matches fn. If not, then the code will create and fill in a file with
    that name from Prizepicks API call. This will override any other flags for local or ow sent in by user.
    '''
    if not os.path.isfile(fn):
        print(f"Problem loading from file '{fn}'")
        exit("Exiting...")

    print(f"Reading from:{fn}")
    with open(fn, 'r') as file:
        wp = file.read()

    print("Read complete!")
    return wp

def hour_run():
    '''
    Function used for testing development and validation of branch for gatting data from the parsed state and into mySQL.
    Takes no arguemtns so that test design is not limited by passed-in vars and returns true when everything passes!!!
    '''
    my_logs.create_loggers()

    for iter in range(60):
        print(f"-------API call #{iter} at time {datetime.datetime.now()}--------")
        scrape_data = web_scraper.new_get_prizepicks("NBA")
        webpage = scrape_data[0]
        scrape_id = scrape_data[1]
        wp_data = my_parser.parse_webpage(webpage)
        print(f"SQL status: {send_to_sql(wp_data, scrape_id)}")
        print(f"...Sleeping...\n")
        time.sleep(60)

if __name__ == "__main__":
    '''
    Eventually, this will be the code that is the manager for the scraper that keep running all the time
    '''
   
    hour_run()
