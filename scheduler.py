import prizepicks_db
import web_scraper
import os
import pickle
from datetime import datetime, timezone, timedelta
import threading
import time
import my_parser
import bisect
import pytz

class prizepicks_scheduler:
    
    scheduler_filename = "scheduler_file.pkl"
    cmd_q = list()
    schedule_rates = dict()
    _db_obj = prizepicks_db.prizepicks_db()
    _stop_loop = False
    is_asleep = False
    known_leagues = [
        "NFL",
        "CFB",
        "MLB",
        "WNBA",
        "Soccer",
        "NBA"
    ]

    loop_wakeup_time = 15 #in seconds, how often the loop should wake up to check for new requests
    
    default_req_rate = 300 # five min in seconds
    min_req_rate = 86400 # one day in seconds
    max_req_rate = 60 # one min in seconds
    
    default_clean_rate = 86400 # one day in seconds
    min_clean_rate = 86400 # one day in seconds
    max_clean_rate = 36000 # ten hours in seconds

    def __init__(self):
        #Constructor for the scheduler class. This will load the queue from a file if it exists, otherwise it will create a default queue.
        if not os.path.isfile(self.scheduler_filename):
            print(f"Scheduler file not found. Creating queue from defaults.")
            self._create_default_queue()
        else:
            self._load_queue_data()
            print(f"Loaded queue from file: {self.scheduler_filename}")
        for each in self.cmd_q:
            print(f"{each}\t{self.schedule_rates[each[1]]}")

    def __del__(self):
        #destructor for the scheduler class. This will save the existing queue data to a file for recovery next time the class is instantiated.
        self._save_queue_data()
        print("Scheduler class cleaned up completely")

    def _save_queue_data(self):
        #Sending queue and request rates to a file so that they can be loaded next time the class is instantiated.
        with open(self.scheduler_filename, 'wb') as scheduler_file:
            q_status = self._queue_data(self.cmd_q, self.schedule_rates)
            pickle.dump(q_status, scheduler_file)

    def _load_queue_data(self):
        #read queue data from file and se the queue and rates to that 
        with open (self.scheduler_filename, 'rb') as scheduler_file:
            saved_q_data = pickle.load(scheduler_file)
        
        #set the queue and rates from the saved data
        self.schedule_rates = saved_q_data.rates
        self.cmd_q = saved_q_data.queue

        #validate that the saved queue and rates are valid. If not, then reset everything to default
        if not self._assert_queue() or not self._assert_rates():
            '''---Post an error here---'''
            print(self.cmd_q)
            print("Saved queue or rates are not valid. Resetting to defaults.")
            self._create_default_queue()

    def _assert_rates(self):
        #function simply to check if all the rates are valid. If not, returns false. otherwise returns true.
        for req_type, rate in self.schedule_rates.items():
            #Make sure that cleaning is happening at an acceptable rate
            if req_type == "clean":
                if rate < self.max_clean_rate or rate > self.min_clean_rate:
                    print(f"Cleaning rate is not within bounds.")
                    return False
            
            #Make sure that the requests are all being made at an acceptable rate
            elif req_type in self.known_leagues:
                if rate < self.max_req_rate or rate > self.min_req_rate:
                    print(f"Request rate for {req_type} is not within bounds")
                    return False
            else:
                print(f"Unknown request type: {req_type}")
                return False
        return True

    def _assert_queue(self):
        #Function which returns true if the queue is valid, false otherwise.

        #Set up objects for tracking what is expected and what is still valid
        queue_items = set(self.known_leagues).union({"clean"})
        remaining_items = set(queue_items)

        for each in self.cmd_q:

            #check that each of the queue items has correct types
            if not isinstance(each, tuple):
                print(f"Queue item {each} is not a tuple.")
                return False
            if len(each) != 2:
                print(f"Queue item {each} does not have length 2.")
                return False
            if not isinstance(each[0], datetime):
                print(f"Queue item {each} does not have a datetime as the first element.")
                return False
            
            #make sure that the request type is valid and not a duplicate
            if each[1] not in queue_items:
                print(f"Queue item {each} has an unknown request type: {each[1]}")
                return False
            if each[1] not in remaining_items:
                print(f"Queue item {each} is a duplicate request type.")
                return False
            
            #If time to execution is further away than the minimum request rate, then that is not valid
            time_to_exec = each[0] - datetime.now(timezone.utc)
            sec_to_exec = time_to_exec.total_seconds()
            if (each[1] in self.known_leagues and sec_to_exec > self.min_req_rate) or (each[1] == "clean" and sec_to_exec > self.min_clean_rate):
                print("Too far in future")
                return False
            
            remaining_items.remove(each[1])
        
        return True

    def _create_default_queue(self):
        #Create queue using all of the default rates for the known leagues and cleanging
        for league in self.known_leagues:
            self.cmd_q.append((datetime.now(timezone.utc), league))
            self.schedule_rates[league] = self.default_req_rate

        self.cmd_q.append((datetime.now(timezone.utc) + timedelta(seconds=self.default_clean_rate), "clean"))
        self.schedule_rates["clean"] = self.default_clean_rate

    def stop_scheduler(self):
        #Function to stop the scheduler loop. This will set the stop flag to true and then wait for the loop to finish next time it is able. Function
        #can be called by the user to stop the scheduler loop gracefully. Function also returns max time the loop will sleep for so caller can know 
        #how long to wait
        print("Stopping scheduler loop...")
        self._stop_loop = True
        return self.loop_wakeup_time

    def run_scheduler(self, runtime_mins = 0):
        #this is the main function which will be called by the user to run the scheduler. This handles the runtime the user specifies.
        
        #If runtime is negative, then nothing to do, raise an error
        if runtime_mins < 0:
            raise ValueError("Runtime minutes must be a non-negative number.")
        
        #If runtime is set to some number of mins, then start a thread to run the scheduler loop and wait for that many minutes before stopping the
        #loop
        elif runtime_mins > 0:
            try:
                action_loop = threading.Thread(target=self._schedule_loop, args=())
                action_loop.start()
                time.sleep(runtime_mins * 60)
            except KeyboardInterrupt:
                print("User input stopping loop prematurely...")

            self.stop_scheduler()
            action_loop.join(timeout = self.loop_wakeup_time+1)
            
            if action_loop.is_alive():
                exit("Houston, we have a problem! Scheduler did not stop in time. Exiting.")
        
        #If runtime is 0, then just run the loop forever until program exits or user stops it
        else:
            self._schedule_loop()

        return True
        
    def _scrape_prizepicks_data(self, league):
        #Funtion which facilitest getting data from PrizePicks and into the DB

        ABORT = 5
        scrape_data = web_scraper.get_prizepicks(league, self._db_obj)

        if isinstance(scrape_data, int):
            '''---Log these errors---'''
            if scrape_data == 1:
                print(f"Legue {league} not recognized by scraper!")

            return (False, scrape_data)

        webpage = scrape_data[0]
        scrape_id = scrape_data[1]
        wp_data = my_parser.parse_webpage(webpage, self._db_obj)
        
        #logging errors posted from parsing fucntion
        if isinstance(wp_data, int):
            consec_errors += 1
            self._db_obj.post_scrape_error(scrape_id, wp_data)
            print(f"!!!FOUND AN ERROR!!!\nErnum: {wp_data} for scrape_id: {scrape_id}")

            '''---Find a way to integrate this without making this function ugly---'''
            '''err_log.error(f"Ernum: {wp_data}\tscrape_id: {scrape_id}\tcons_count: {consec_errors}")
            if consec_errors >= SNAPSHOT:
                save_wp_snapshot(webpage, scrape_id, consec_errors)'''
            if consec_errors >= ABORT:
                print(f"Consecutive errors exceeded limit of {ABORT}. Aborting run.")
                exit("Exiting...")
       
        #If no errors are found, then send the data to the database
        else:
            '''---Perhaps log the sql status rather than print it out?---'''
            print(f"SQL status: {self._db_obj.send_to_sql(wp_data, scrape_id)}")
            consec_errors = 0
        
        return (True, wp_data)
    
    def _q_sanity_check(self, cmd_type):
        #Function which quickly checks to make sure there is exactly 1 instance of cmd_type in the q. If 0 or more than 1 instance in the q.
        #If 0 instances, returns 0
        #If >1 instance, return 2
        #Otherwise, return 1

        found_cmd = False
        for i, cmd in enumerate(self.cmd_q):
            
            #First instance found
            if cmd[1] == cmd_type and found_cmd is False:
                found_cmd = True
            
            #second instance found
            elif cmd[1] == cmd_type and found_cmd is True:
                return 2
        
        #Got to end with nothing found
        if found_cmd is False:
            return 0
        
        return 1

    def _update_req_freq(self, cmd_type, game_data):
        #Takes a look at when the next game for a specific league is and dynamically schedules when the next time it should be scheduled is
        #There are 2 assumptions made in the logic of this function:
        #1) that as a player gets closer to gametime, their spread is more likely to change
        #This function will look at both time since the game was created and time until the same is supposed to start and decide frequency based on the
        #event closest in time (in future or past)

        #None can indicate 2 things: 1 that something went wrong and no data was parsed or 2 that there are in fact no upcoming games and the season
        #is over or no bets are available.
            #So not to overcompensate for the case of #1, will double the refresh time
        if game_data is None:
            '''---Good to log to make sure this is behaving as expected---'''
            self.schedule_rates[cmd_type] = min( self.schedule_rates[cmd_type]*2, self.min_req_rate )
            return
        
        #The next game being >28 days away will trigger lowest request rate, so start with this and then see if any are sooner than that
        next_game = datetime.now(timezone.utc) + timedelta( days=28 )

        #go through each game and check if it is earlier than the next_game
        for game in game_data:
            
            #Make sure the data for game start time exists in parsed object, if not, go to the next entry
            start_time = game.get('start_time')
            if start_time is not None:
                start_time = datetime.fromisoformat(start_time).astimezone(timezone.utc)
                if start_time < next_game:
                    next_game = start_time
        
        sec_to_nxt_gm = (next_game - datetime.now(timezone.utc)).total_seconds()
        four_wks = 2419200
        one_wk = 604800
        four_days = 345600
        one_day = 86400
        six_hrs = 21600
        three_hrs = 10800
        one_hr = 3600
        thrty_mins = 1800
        fiften_mins = 900
        five_mins = 300
        two_mins = 120        

        #over one month away, just check once a day
        if sec_to_nxt_gm > four_wks:
            self.schedule_rates[cmd_type] = self.min_req_rate 

        #4-1 week away
        elif sec_to_nxt_gm > one_wk:
            self.schedule_rates[cmd_type] = one_hr

        #7-4 days away
        elif sec_to_nxt_gm > four_days:
            self.schedule_rates[cmd_type] = thrty_mins

        #4-1 day away
        elif sec_to_nxt_gm > one_day:
            self.schedule_rates[cmd_type] = fiften_mins

        #24-6 hrs away
        elif sec_to_nxt_gm > six_hrs:
            self.schedule_rates[cmd_type] = five_mins

        #6-3 hrs away
        elif sec_to_nxt_gm > three_hrs:
            self.schedule_rates[cmd_type] = two_mins

        #3-0 hrs away
        elif sec_to_nxt_gm > 0:
            self.schedule_rates[cmd_type] = self.max_req_rate
        
        #Negative time should not be possible, this needs to be checked! Setting to default 
        else:
            '''---Log this---'''
            print("Time to next game is negative, that should not be possible, resetting to default")
            self.schedule_rates[cmd_type] = self.default_req_rate

        return

    def _update_queue(self, data):
        #update queue once a command has been executed and make adjustments to scheduler as-needed
        
        #---Updaing the queue---
        #Since each command can only be in the q once, this just takes the command just executed (at spot 0), adds the request rate for that command
        #type to the current time, then inserts it back into the queue in order

        #---Updating the request rate---
        #I assume that as we get closer to gametime, spreads are going to change more often. To make sure I'm not making more requests to the
        #prizepicks API than needed. Since each API call gets all the data each time, I'm just going to make my calls based on the next game to occur
        #so this find the next most recent game time and computes when the next request should be from that.

        cmd_type = self.cmd_q[0][1]

        #Make sure there is data to check against, if not then no need to adjust frequencies
        if data is not None:
            #today the function only needs the game data, so just send what the fucntion needs
            self._update_req_freq(cmd_type, data.included_tag_values.get('game'))

        bisect.insort(self.cmd_q, (datetime.now(timezone.utc) + timedelta(seconds=self.schedule_rates[cmd_type]), cmd_type))
        self.cmd_q.pop(0)

        return True
    
    def _print_q_status(self):
        #Function to print the current status of the queue to the console

        print("\t---Queue status---")
        for sch,cmd in self.cmd_q:
            print(f"\t{sch.astimezone().isoformat()}\t{cmd}\t{self.schedule_rates[cmd]}")
        print("\t------------------")

    def _schedule_loop(self):
        #this is the loop which will schedule the commands to be executed. This will run until the _stop_loop flag is set to true.
        self._stop_loop = False
        min_time_to_wait = 5 #in seconds to avoid spamming the API with requests and being detected

        while True:
            if self._stop_loop:
                print("Scheduler loop stopped gracefully.")
                break

            #Checking to see if it is time to execute the next command in the queue
            nxt_cmd = self.cmd_q[0]
            my_delta = nxt_cmd[0] - datetime.now(timezone.utc)
            sec_to_exec = my_delta.total_seconds()
            data = None

            #If next command is ready to be executed, then execute it
            if sec_to_exec < (self.loop_wakeup_time/2):

                cmd_type = nxt_cmd[1]
                status = False
                if cmd_type == "clean":
                    print("Executing db cleaning")
                    status = self._db_obj.clean_db()

                elif cmd_type in self.known_leagues:
                    print(f"Executing command {cmd_type}")
                    status, data = self._scrape_prizepicks_data(cmd_type)

                else:
                    raise TypeError(f"Unknown command type: {cmd_type}")
                
                if status is False:
                    #---Log this error---
                    print("Problem found executing command...")
                    raise RuntimeError(f"Command {cmd_type} failed to execute properly. Status = {status}")
                
                self._update_queue(data)

            else:
                print("Woke up but nothing to execute. Here is current q:")
            
            self._print_q_status()

            #Tell the loop to sleep until either the next wakeup time or the next command execution time.
            #I do put a limit on here that the loop will not sleep for less than 5 seconds, to avoid spamming the API.
            sleep_time = min( self.loop_wakeup_time,max( min_time_to_wait,sec_to_exec ) )
            print(f"Sleep time: {sleep_time} sec")
            try:
                time.sleep( sleep_time )
            except KeyboardInterrupt:
                print("User input stopping execution early!")
                self._stop_loop = True
                break

        #If loop is gracefully broken out of, then reset the stop flag so it can be restarted without issue if needed
        self._stop_loop = False
        return True

    #class to hold all the relevant queue data from scheduler class when it is destructed. this way the data persists even if the class is deleted
    class _queue_data:
        queue = list()
        rates = dict()

        def __init__(self, caller_queue, caller_rates):
            self.queue = caller_queue
            self.rates = caller_rates

