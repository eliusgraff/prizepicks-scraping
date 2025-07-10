import os
from web_scraper import get_prizepicks
import my_parser
from prizepicks_db import prizepicks_db
import my_logs
import datetime
import time
import logging
from scheduler import prizepicks_scheduler as sch

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

def save_wp_snapshot(wp, scrapenum, count):
    curdir_path = os.path.dirname(__file__)
    log_path = f"{str(curdir_path)}\\logs\\"
    fn = f"{log_path}Snapshot_{scrapenum}_{count}.txt"
    save_wp_data(wp, fn)
    print(f"Saved snapshot to {fn}")

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
    err_log = logging.getLogger("err_log")
    consec_errors = 0
    SNAPSHOT = 2
    ABORT = 5
    pp_db = prizepicks_db()
    my_range = 240

    for iter in range(my_range):
        print(f"-------API call #{iter}/{my_range} at time {datetime.datetime.now()}--------")
        scrape_data = get_prizepicks("NBA", pp_db)
        webpage = scrape_data[0]
        scrape_id = scrape_data[1]
        wp_data = my_parser.parse_webpage(webpage, pp_db)
        
        #logging errors posted from parsing fucntion
        if isinstance(wp_data, int):
            consec_errors += 1
            pp_db.post_scrape_error(scrape_id, wp_data)
            print(f"!!!FOUND AN ERROR!!!\nErnum: {wp_data} for scrape_id: {scrape_id}")
            err_log.error(f"Ernum: {wp_data}\tscrape_id: {scrape_id}\tcons_count: {consec_errors}")
            if consec_errors >= SNAPSHOT:
                save_wp_snapshot(webpage, scrape_id, consec_errors)
            if consec_errors >= ABORT:
                print(f"Consecutive errors exceeded limit of {ABORT}. Aborting run.")
                exit("Exiting...")

        else:
            print(f"SQL status: {pp_db.send_to_sql(wp_data, scrape_id)}")
            consec_errors = 0
        print(f"...Completed #{iter}/{my_range}...\n...Sleeping...\n")
        time.sleep(30)

def trial():
    x = prizepicks_db()
    trials = [
        [4001021,4001022,4001023,4001024,4001025,4001026],
        [4001021],
        ['4001021','4001022','4001023','4001024','4001025','4001026'],
        [],
        None
    ]
    for test_list in trials:
        print("Test list:")
        print(test_list)
        table_name = 'projection'
        base_sql = f"Select * FROM {table_name} "
        where_clause = "" if test_list is None else f"WHERE ID in ({','.join([str(x) for x in test_list])})"
        sql = base_sql + where_clause
        print(f"my query: {sql}")
        print(x.read_query(sql))
        print("-----------")

if __name__ == "__main__":
    '''
    Eventually, this will be the code that is the manager for the scraper that keep running all the time
    '''
    s = sch()
    s.run_scheduler(120)
    del s
