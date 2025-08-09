import prizepicks_db
import web_scraper
import os
import pickle
from datetime import datetime, timezone, timedelta
import threading
import time
import my_parser
import bisect
import logging
from logging.handlers import RotatingFileHandler
import json
import traceback

class prizepicks_scheduler:
    
    scheduler_filename = "scheduler_file.pkl" #filename where the scheduler info is stored when scheduler is deleted
    cmd_q = list() #queue to track the order of commands the be executed, in the order they will be executed in
    schedule_rates = dict() #polling rate for each of the types of commands in the cmd_q
    _db_obj = prizepicks_db.prizepicks_db() #connection to the prizepicks db
    _stop_loop = False #bool to track whether the scheduler loop is going or not. Allows for programatic way to kill the loop from parent thread
    is_asleep = False #bool to track whether the scheduler loop is sleeping in between api polls or is processing data
    known_leagues = [
        "NFL",
        "CFB",
        "MLB",
        "WNBA",
        "Soccer",
        "NBA",
        "sts"
    ]

    loop_wakeup_time = 15 #in seconds, how often the loop should wake up to check for new requests
    default_req_rate = 300 # five min in seconds
    min_req_rate = 86400 # one day in seconds
    max_req_rate = 60 # one min in seconds
    status_rate = 3600 # one hour in seconds - will update db status every hour

    stats_log = None # logger object for db stats logging
    sched_log = None # logger object for scheduler logging
    err_log = None # logger object for error logging
    trace_log = None # logger object for tracing command flow of the project
    log_path = f"{str(os.path.dirname(__file__))}\\logs"

    scrape_errors = 0 # counter for how many consecutive scrape error are seen
    scrape_errtype = dict() # dict to keep track of consec scrape errors on a by-league basis
    parse_errors = 0 # counter for how many consecutive parser errors are seen
    parse_errtype = dict() # dict to keep track of consec parse errors on a by-league basis
    SNAP = 3 # number of allowable consecutive errors before a snapshot is taken of the api response
    ABORT = 5 # number of allowable consecutive errors before the scheduler will kill itself and stop making requests


    def __init__(self):
        #Constructor for the scheduler class. 
        
        #Set up loggers
        self._create_loggers()
        self.trace_log.critical("INIT")

        #Load in queue data from a file if it exists, otherwise create a default queue.
        if not os.path.isfile(self.scheduler_filename):
            self.err_log.warning(f"1: {self.scheduler_filename}")
            self._create_default_queue()
        
        else:
            #Load data from file and validate that it is valid
            resp = self._load_queue_data()
            
            #If the loaded q data is not valid, then log appropriate info for debug
            if resp is not True:
                self.err_log.warning(f"2_{resp}: {self.scheduler_filename}")
                q_msg = "curq: "
                for sch,cmd in self.cmd_q:
                    q_msg += f"{sch.astimezone().isoformat()}:{cmd}:{self.schedule_rates[cmd]}\t"
                self.err_log.debug(f"\t{q_msg[:-1]}")
        
        for each in self.cmd_q:
            self.sched_log.debug(f"\t{each}  {self.schedule_rates[each[1]]}")

    def __del__(self):
        #destructor for the scheduler class. This will save the existing queue data to a file for recovery next time the class is instantiated.
        self._save_queue_data()
        self.trace_log.info("DEL")

    def _create_loggers(self):
        #Function to create loggers for the scheduler class. 2 logers are created, one to keep track of the stats of the DB so the size can be 
        #monitored over time and one to keep track of any error which may occur during operation

        '''---Need to find a logical way to decide how large these logs are allowed to be---'''
        #Make sure that the logs directory exists, if not, make it
        if not os.path.isdir(self.log_path): 
            os.mkdir(self.log_path)

        #Set up stats logger
        stats_logname = f"{__name__}_stats"
        self.stats_log = logging.getLogger(stats_logname)
        self.stats_log.setLevel("INFO")
        stats_file_handler = RotatingFileHandler(f"{self.log_path}\\{stats_logname}.log", maxBytes=50000000, backupCount=5)
        stats_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.stats_log.addHandler(stats_file_handler)

        #Set up scheduler log
        sched_logname = f"{__name__}_sched"
        self.sched_log = logging.getLogger(sched_logname)
        self.sched_log.setLevel("INFO")
        sched_log_file_handler = RotatingFileHandler(f"{self.log_path}\\{sched_logname}.log", maxBytes=5000000, backupCount=3)
        sched_log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.sched_log.addHandler(sched_log_file_handler)

        #set up tracepoint logger
        trace_logname = f"{__name__}_trace"
        self.trace_log = logging.getLogger(trace_logname)
        self.trace_log.setLevel("INFO")
        trace_log_file_handler = RotatingFileHandler(f"{self.log_path}\\{trace_logname}.log", maxBytes=5000000, backupCount=3)
        trace_log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.trace_log.addHandler(trace_log_file_handler)

        #set up error logger
        err_logname = f"{__name__}_err"
        self.err_log = logging.getLogger(err_logname)
        self.err_log.setLevel("INFO")
        err_log_file_handler = RotatingFileHandler(f"{self.log_path}\\{err_logname}.log", maxBytes=5000000, backupCount=3)
        err_log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.err_log.addHandler(err_log_file_handler)

    def _save_queue_data(self):
        #Sending queue and request rates to a file so that they can be loaded next time the class is instantiated.
        with open(self.scheduler_filename, 'wb') as scheduler_file:
            q_status = self._queue_data(self.cmd_q, self.schedule_rates)
            pickle.dump(q_status, scheduler_file)

    def _load_queue_data(self):
        #read queue data from file and set the rates according to that 
        with open (self.scheduler_filename, 'rb') as scheduler_file:
            saved_q_data = pickle.load(scheduler_file)
        
            #set the queue and rates from the saved data
            self.schedule_rates = saved_q_data.rates
            self.cmd_q = saved_q_data.queue

        #validate that the saved queue and rates are valid. If not, log the bad q and then reset everything to default
        if not self._assert_queue() or not self._assert_rates():
            self._create_default_queue()
            return 1
        
        return True

    def _assert_rates(self):
        #function simply to check if all the rates are valid. If not, returns false. otherwise returns true.
        for req_type, rate in self.schedule_rates.items():
            
            #Make sure that the requests are all being made at an acceptable rate
            if req_type in self.known_leagues:
                if rate < self.max_req_rate or rate > self.min_req_rate:
                    self.err_log.debug(f"1: t={req_type} r={rate}")
                    return False
            #If req_type is not in known leagues, then that is also a problem!
            else:
                self.err_log.debug(f"2: t={req_type} r={rate}")
                return False
        return True

    def _assert_queue(self):
        #Function which returns true if the queue is valid, false otherwise.

        #Set up objects for tracking what is expected and what is still valid
        queue_items = set(self.known_leagues)
        remaining_items = set(queue_items)

        for each in self.cmd_q:

            #check that each of the queue items has correct types
            '''---Return code rather than false for everything---'''
            
            if not isinstance(each, tuple):
                #Queue item {each} is not a tuple
                self.err_log.warning(f"1: {each}")
                return False #return 1
            
            if len(each) != 2:
                #Queue item must have length 2
                self.err_log.warning(f"2: {each}")
                return False #return 2
            
            if not isinstance(each[0], datetime):
                #Queue item must have a datetime as the first element
                '''---Could try to parse this as a string to go to datetime, that may be elegant way to handle errors here---'''
                self.err_log.warning(f"3: {each}")
                return False #return 3
            
            #make sure that the request type is valid and not a duplicate
            if each[1] not in queue_items:
                #Queue item must have known command type at each[1]
                self.err_log.warning(f"4: {each}")
                return False #return 4
            
            if each[1] not in remaining_items:
                #Queue item must not be a duplicate
                self.err_log.warning(f"5: {each}")
                return False #return 5
            
            #If time to execution is further away than the minimum request rate, then that is not valid
            time_to_exec = each[0] - datetime.now(timezone.utc)
            sec_to_exec = time_to_exec.total_seconds()
            if each[1] in self.known_leagues and sec_to_exec > self.min_req_rate :
                #Next scheduled time for this command must be within minimum polling constraints
                '''---Could I handle this gracefully and just add it back in at the minimum sample rate?---'''
                self.err_log.warning(f"6: {each}")
                return False #return 6
            
            remaining_items.remove(each[1])
        
        #If there are any items missing, add them to the queue with default rate
        if len(remaining_items) > 0:
            self.err_log.warning(f"7: {', '.join(cmd for cmd in remaining_items)[:-1]}")
        for each in remaining_items:

            self.cmd_q.append((datetime.now(timezone.utc), each))

            if each == 'sts':
                self.schedule_rates[each] = self.status_rate
            else:
                self.schedule_rates[each] = self.default_req_rate

        return True

    def _create_default_queue(self):
        #Create queue using all of the default rates for the known leagues
        
        self.cmd_q = list()
        for league in self.known_leagues:
            self.cmd_q.append((datetime.now(timezone.utc), league))
            self.schedule_rates[league] = self.default_req_rate
        self.schedule_rates['sts'] = self.status_rate

    def stop_scheduler(self):
        #Function to stop the scheduler loop. This will set the stop flag to true and then wait for the loop to finish next time it is able. Function
        #can be called by the user to stop the scheduler loop gracefully. Function also returns max time the loop will sleep for so caller can know 
        #how long to wait
        '''---Log this---'''
        print("Stopping scheduler loop...")
        self.trace_log.info(f"0")
        self._stop_loop = True
        return self.loop_wakeup_time

    def run_scheduler(self, runtime_mins = 0):
        #this is the main function which will be called by the user to run the scheduler. This handles the runtime the user specifies.

        #If runtime is negative, then nothing to do, raise an error
        if runtime_mins < 0:
            self.err_log.error(f"1: {runtime_mins}")
            raise ValueError("Runtime minutes must be a non-negative number.")
        
        self.trace_log.info(f"0: {runtime_mins}")

        #If runtime is set to some number of mins, then start a thread to run the scheduler loop and wait for that many minutes before stopping the
        #loop
        if runtime_mins > 0:
            try:
                action_loop = threading.Thread(target=self._schedule_loop, args=())
                action_loop.start()
                time.sleep(runtime_mins * 60)
            except KeyboardInterrupt:
                #User input stopping loop before timeout
                self.trace_log.info(f"00: {runtime_mins}")

            #stopping scheduler gently and rejoining child thread 
            self.stop_scheduler()
            action_loop.join(timeout = self.loop_wakeup_time+1)
            
            #If child doesn't rejoin in reasonable time, then kill the whole scheduler
            if action_loop.is_alive():
                self.err_log.critical(f"1")
                exit("Houston, we have a problem! Scheduler did not stop in time. Exiting.")
        
        #If runtime is 0, then just run the loop forever until program exits or user stops it
        else:
            self._schedule_loop()

        return True
        
    def _scrape_prizepicks_data(self, league):
        #Funtion which facilitates getting data from PrizePicks and into the DB
        
        self.trace_log.info(f"{league}")
        
        #Make call to the prizepicks API to get the data
        scrape_data = web_scraper.get_prizepicks(league, self._db_obj)

        #Return false if there was an error with the scrape by returning and send the error code
        if isinstance(scrape_data, int):
            self.scrape_errors += 1
            self.scrape_errtype[league] += 1
            self.err_log.error(f"1_{scrape_data}: {league}")

            #the only reason this should post an error is if the league is not known to the scraper, tracking here so I can see what's going on
            if self.scrape_errors > self.SNAP or self.scrape_errtype[league] > self.SNAP:
                self.err_log.critical(f"2: lgnum={league} - se={self.scrape_errors} - errtyp={self.scrape_errtype}")
            if self.scrape_errors > self.ABORT:
                exit(f"Too many consecutive scrape errors for {league}, exiting...")
            
            return (False, scrape_data)

        #reset error counters
        self.scrape_errors = 0
        self.scrape_errtype[league] = 0

        #Send the webpage data to the parser
        webpage = scrape_data[0]
        scrape_id = scrape_data[1]
        
        '''---REAllY REALLY REALLY NEED TO UPDATE THIS SO THAT ERRNUMS ARE RETURNED RATHER THAN JUST CATCHING EVERYTHING---'''
        try:
            wp_data = my_parser.parse_webpage(webpage, self._db_obj)
            self._db_obj.send_to_sql(wp_data, scrape_id)

        except Exception as e:
            #Since there is no meaningful error codes in teh parsing and sql modules today, I'm just going to catch everything and log it all so that 
            #I can try and troubleshoot the issue for the time being before I try and go back and refactor to add in error numbering and reporting
            self._db_obj.post_scrape_error(scrape_id, wp_data)
            ex_snap_fn = self._exc_snap("parse",e)
            json_snap_fn = self._json_snap("parse",wp_data)
            self.err_log.error(f"3: scrid={scrape_id} - lg={league} - ex={type(e.__name__)} - excfn={ex_snap_fn} - jsonfn={json_snap_fn}")

            if self.parse_errors > self.ABORT or self.parse_errtype[league] > self.ABORT:
                exit("Too many consecutive parsing errors... exiting")
            self.parse_errors += 1
            self.parse_errtype[league] += 1
            return (False, wp_data)

        #Reset the parse error counters
        self.parse_errors = 0
        self.parse_errtype[league] = 0
        
        return (True, wp_data)
    
    def _q_sanity_check(self, cmd_type):
        #Function which checks to make sure there is exactly 1 instance of cmd_type in the q. If 0 or more than 1 instance in the q.
        #If 0 instances, returns 0
        #If >1 instance, return 2
        #Otherwise, return 1

        found_cmd = False
        for cmd in self.cmd_q:
            
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
        #Takes a look at when the next game for a specific league is and schedules when the next time it should be scheduled is
        #The assumption made in the design of this function is that as a player gets closer to gametime, their spread is more likely to change
        #This function will look at both time since the game was created and time until the game is supposed to start and decide frequency based on the
        #event closest in time (in future or past)

        #None can indicate 2 things: 1 that something went wrong and no data was parsed or 2 that there are in fact no upcoming games and the season
        #is over or no bets are available.
            #So not to overcompensate for the case of #1, will double the refresh time
        if game_data is None:
            self.schedule_rates[cmd_type] = min( self.schedule_rates[cmd_type]*2, self.min_req_rate )
            return (0,cmd_type,self.schedule_rates[cmd_type])
        
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
            #Time to next game is negative, that should not be possible, logging it and resetting to default
            '''---Maybe there is a way I can store other game info so that rather than just going to default I can just use the last valid gametime---'''
            self.schedule_rates[cmd_type] = self.default_req_rate
            return (1, cmd_type, next_game, sec_to_nxt_gm)
        
        return True

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

        #Make sure there is data to check against, if not then no need to adjust frequencies. Also if the commands is just stats update, then that is 
        #done at constant interval so nothing to update
        if data is not None and data != 'sts':
            #today the function only needs the game data, so just send what the fucntion needs
            ec = self._update_req_freq(cmd_type, data.included_tag_values.get('game'))
            
            #If ec is not true then there is info returned to this fucntion to be logged
            if ec is not True:
                #ec 0 is when there are no games found for a parse. This is not a problem, but just logging it for now
                if ec[0] == 0:
                    self.sched_log.info(f"00: cmd={ec[1]} - r8={ec[2]}")

                #ec 1 is when a gametime is scheduled for some time in the past. This is not expected to happen so it is logged as an error. This is 
                #handled in the _update_req_freq function
                elif ec[0] == 1:
                    err_msg = f"1: cmd={ec[1]} - nxt={ec[2]} - ttg={ec[3]}"
                    self.sched_log.error(err_msg)
                    self.err_log.error(err_msg)
        
        bisect.insort(self.cmd_q, (datetime.now(timezone.utc) + timedelta(seconds=self.schedule_rates[cmd_type]), cmd_type))
        self.cmd_q.pop(0)

        return True
    
    def _log_q_status(self, sleep_time = None):
        #Function to log current status of the queue and how long the loop is going to sleep for
        q_msg = "curq: "
        for sch,cmd in self.cmd_q:
            q_msg += f"{sch.astimezone().isoformat()}:{cmd}:{self.schedule_rates[cmd]}\t"
        self.sched_log.info(f"\t{q_msg[:-1]}")

        if sleep_time is not None:
            slp_msg = f"slp: {sleep_time}sec"
            self.sched_log.info(slp_msg)

    def _schedule_loop(self):
        #this is the loop which will schedule the commands to be executed. This will run until the _stop_loop flag is set to true.        

        self._stop_loop = False
        min_time_to_wait = 5 #in seconds to avoid spamming the API with requests and being detected

        self.trace_log.debug("0")
        while True:
            if self._stop_loop:
                #Scheduler loop stopped gracefully
                self.trace_log.info("00")
                break

            #Checking to see if it is time to execute the next command in the queue
            nxt_cmd = self.cmd_q[0]
            my_delta = nxt_cmd[0] - datetime.now(timezone.utc)
            sec_to_exec = my_delta.total_seconds()
            data = None

            #execute next command if it is scheduled to be done before the next time the loop is supposed to wake up
            exec_cmd = sec_to_exec < (self.loop_wakeup_time/2)

            #If next command is ready to be executed, then execute it
            if exec_cmd:

                cmd_type = nxt_cmd[1]
                status = False

                #If the command is not recognized, then raise error
                if cmd_type not in self.known_leagues:
                    err_msg = f"1: unknwncmd={cmd_type}"
                    self.err_log.critical(err_msg)
                    self.sched_log.critical(err_msg)
                    raise TypeError(f"Unknown command type: {cmd_type}")
            
                if cmd_type == 'sts':
                    status = self._get_db_stats()
                else:
                    status, data = self._scrape_prizepicks_data(cmd_type)

                if status is False:
                    #Problem found executing command...
                    self.err_log.error(f"2: cmd={cmd_type} - stus={status}")
                    raise RuntimeError(f"Command {cmd_type} failed to execute properly. Status = {status}")
                
                self._update_queue(data)

            #If woken up and nothing to do, then go right on back to sleep
            else:
                self.trace_log.debug("00")
            

            #Tell the loop to sleep until either the next wakeup time or the next command execution time.
            #I do put a limit on here that the loop will not sleep for less than 5 seconds, to avoid spamming the API or more than 15 seconds to avoid
            # situation where the loop cannot be cancelled by the caller.
            sleep_time = min( self.loop_wakeup_time,max( min_time_to_wait,sec_to_exec ) )
            
            #To avoid spam, only log q status if something has been executed
            if exec_cmd: self._log_q_status(sleep_time)
            
            try:
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                print("User input stopping execution early!")
                self._stop_loop = True
                break

        #If loop is gracefully broken out of, then reset the stop flag so it can be restarted without issue if needed
        self._stop_loop = False
        return True
    
    def _get_db_stats(self):
        #Function to get the size of the tables in the db and log them
        db_stats = self._db_obj.get_stats()
        mystr = "tbszs(mb): "
        for name, size in db_stats:
            mystr += f"{name}:{size}\t"
        self.stats_log.info(mystr)
        return True
    
    def _purge_q(self, name):
        #utility funtion used for deleting certain commands out of the q. This will take in a name delete all commands with that name from the q

        self.trace_log.critical(f"0: nm={name}")
        rmvd = False

        for i, cmd_name in enumerate(self.cmd_q):
            if cmd_name[1] == name:
                del self.cmd_q[i]
                rmvd = True
                log_msg = f"00: rmvd={cmd_name}"
                self.trace_log.info(log_msg)
                self.sched_log.info(log_msg)

        if rmvd is False:
            #log the case where the command was found/deleted
            self.trace_log.warning(f"01: ntfnd={name}")

        #remove the command from the schedule rates
        try:
            del self.schedule_rates[name]
            log_msg = f"000: rmvd={cmd_name}"
            self.trace_log.info(log_msg)
            self.sched_log.info(log_msg)  

        except KeyError:
            self.trace_log.warning(f"02: ntfnd={name}")

    def _create_snap_fn(self, prefix):
        #Centralizing file naming schema for all the snapshot
        return f"{self.log_path}\\{prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

    def _json_snap(self, prefix, data):
        #Function to take a json object and send it to a text file for review why this may have given the program a hard time. Return fn to I can 
        #correlate the error to the dump
        fn = self._create_snap_fn(prefix)
        with open(fn,"w") as json_file:
            json.dump(data, json_file, indent=4)
        self.trace_log.debug(f"0: fn={fn}")
        return fn

    def _exc_snap(self, prefix, e):
        #Function to take in an exception object and send it to a text file for logging and review purposes
        fn = self._create_snap_fn(prefix)
        with open(fn,"w") as f:
            f.write(f"{type(e).__name__}\n")
            f.write(f"{e}\n")
            f.write(traceback.format_exc()) # Get the formatted traceback string
            
        self.trace_log.debug(f"0: fn={fn}")
        return fn


    #class to hold all the relevant queue data from scheduler class when it is destructed. this way the data persists even if the class is deleted
    class _queue_data:
        queue = list()
        rates = dict()

        def __init__(self, caller_queue, caller_rates):
            self.queue = caller_queue
            self.rates = caller_rates

