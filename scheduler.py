import prizepicks_db
import web_scraper
import os
import pickle
from datetime import datetime, timezone, timedelta
import threading
import time
import my_parser
import bisect

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
    
    default_req_rate = 300 #in seconds
    min_req_rate = 86400 #in seconds
    max_req_rate = 30 #in seconds
    
    default_clean_rate = 86400 #in seconds
    min_clean_rate = 86400 #in seconds
    max_clean_rate = 3600 #in seconds

    def __init__(self):
        #Constructor for the scheduler class. This will load the queue from a file if it exists, otherwise it will create a default queue.
        if not os.path.isfile(self.scheduler_filename):
            print(f"Scheduler file not found. Creating queue from defaults.")
            self._create_default_queue()
        else:
            self._load_queue_data()
            print(f"Loaded queue from file: {self.scheduler_filename}")
        for each in self.cmd_q:
            print(each)

    def __del__(self):
        #destructor for the scheduler class. This will save the existing queue data to a file for recovery next time the class is instantiated.
        self._save_queue_data()

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
            action_loop = threading.Thread(target=self._schedule_loop, args=())
            action_loop.start()
            time.sleep(runtime_mins * 60)
            self.stop_scheduler()
            action_loop.join(timeout = self.loop_wakeup_time+1)
            if action_loop.is_alive():
                exit("Houston, we have a problem! Scheduler did not stop in time. Exiting.")
        
        #If runtime is 0, then just run the loop forever until program exits or user stops it
        else:
            self._schedule_loop()

        return True
    
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
            
            #If next command is ready to be executed, then execute it
            if sec_to_exec < (self.loop_wakeup_time/2):

                cmd_type = nxt_cmd[1]
                '''status = False
                if cmd_type == "clean":
                    status = self._db_obj.clean_db()

                elif cmd_type in self.known_leagues:
                    status = self._scrape_prizepicks_data(cmd_type)

                else:
                    raise TypeError(f"Unknown command type: {cmd_type}")
                
                if status is False:
                    #---Log this error---
                    print("Problem found executing command...")
                    raise RuntimeError(f"Command {cmd_type} failed to execute properly.")'''
                print(f"Executing command: {cmd_type}")

                if self._update_queue() == False:
                    '''---Log this error---'''
                    print("Problem updating queue after command execution.")
                    raise RuntimeError("Queue update failed after command execution.")

            #Tell the loop to sleep until either the next wakeup time or the next command execution time.
            #I do put a limit on here that the loop will not sleep for less than 5 seconds, to avoid spamming the API.
            sleep_time = min( self.loop_wakeup_time,max( min_time_to_wait,sec_to_exec ) )
            print(f"Sleep time: {sleep_time}")
            time.sleep( sleep_time )

        #If loop is gracefully broken out of, then reset the stop flag so it can be restarted without issue if needed
        self._stop_loop = False
        return True
    
    def _scrape_prizepicks_data(self, league):
        #Funtion which facilitest getting data from PrizePicks and into the DB

        ABORT = 5
        scrape_data =web_scraper.get_prizepicks(league, self._db_obj)
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
        
        return True

    def _update_queue(self):
        #update queue once a command has been executed. 

        #requeue same command back at newly scheduled time in the queue

        '''---Eventually add some logic in here to schedule things with no upcoming games less often than things that do---'''

        cmd_type = self.cmd_q[0][1]
        bisect.insort(self.cmd_q, (datetime.now(timezone.utc) + timedelta(seconds=self.schedule_rates[cmd_type]), cmd_type))

        #remove executed command
        self.cmd_q.pop(0)

        return True

    #class to hold all the relevant queue data from scheduler class when it is destructed. this way the data persists even if the class is deleted
    class _queue_data:
        queue = list()
        rates = dict()

        def __init__(self, caller_queue, caller_rates):
            self.queue = caller_queue
            self.rates = caller_rates

