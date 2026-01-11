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
from utils import debug_exc
from threading import Thread #enumerate - Need to import this as something else since enumerate is a funciton in the python standard library and this conflicts with that
import traceback
import subprocess

FOUR_WKS = 2419200
ONE_WK = 604800
FOUR_DAYS = 345600
ONE_DAY = 86400
TWELVE_HOURS = 43200
SIX_HOURS = 21600
THREE_HOURS = 10800
ONE_HOUR = 3600
THIRTY_MINS = 1800
FIFTEEN_MINS = 900
TEN_MINS = 600
FIVE_MINS = 300
TWO_MINS = 120
ONE_MIN = 60
FIFTEEN_SEC = 15
FIVE_SEC = 5

class prizepicks_scheduler:
    
    scheduler_filename = os.path.join(os.path.dirname(__file__),"scheduler_file.pkl") #filename where the scheduler info is stored when scheduler is deleted
    cmd_q = list() #queue to track the order of commands the be executed, in the order they will be executed in
    schedule_rates = dict() #polling rate for each of the types of commands in the cmd_q
    _db_obj = prizepicks_db.prizepicks_db() #connection to the prizepicks db
    _stop_loop = False #bool to track whether the scheduler loop is going or not. Allows for programatic way to kill the loop from parent thread
    is_asleep = False #bool to track whether the scheduler loop is sleeping in between api polls or is processing data
    
    '''---Uncomment these---'''
    known_leagues = [
        "NFL",
        "CFB",
        #"MLB",
        #"WNBA",
        #"Soccer",
        #"NBA",
        "NHL",
        #"TENNIS"
    ]

    default_req_rate = FIVE_MINS
    min_req_rate = ONE_DAY
    
    '''---Need to change this back to be ONE_MIN---'''
    max_req_rate = FIVE_MINS

    #Dictionary to keep track of all of the non-essential 'background' activities that happen and the rate at which they should be scheduled
    background = {
        "sts":ONE_DAY,
        "dmp_sch":TEN_MINS,
        "bu":ONE_DAY,
        "archive":TWELVE_HOURS
    }

    loop_wakeup_time = FIFTEEN_SEC #how often the loop should wake up to check for new requests

    stats_log = None # logger object for db stats logging
    sched_log = None # logger object for scheduler logging
    err_log = None # logger object for error logging
    trace_log = None # logger object for tracing command flow of the project
    log_path = os.path.join(os.path.dirname(__file__),"logs")

    parse_errors = 0 # counter for how many consecutive parser errors are seen
    parse_errtype = dict() # dict to keep track of consec parse errors on a by-league basis
    SNAP = 3 # number of allowable consecutive errors before a snapshot is taken of the api response
    ABORT = 5 # number of allowable consecutive errors before the scheduler will kill itself and stop making requests

    _bu_thread = Thread() # Thread object which will be managing the occasional backups in the background. I will only allow one singe backup thread at a time, so this will help enforce that

    #Constructor for the scheduler class. 
    def __init__(self):
        input("THIS IS A DEVELOPMENT VERSION, BEFORE PUSHONG PLEASE UPDATE THE MEMBER VARIABLES BEFORE PRODUCTION ENVIRONMENT")
        print("Setting up Scheduler class...")
        #Set up loggers
        self._create_loggers()
        self.trace_log.critical("INIT")
        self.create_queue()     
        self._log_q_status()

    #Destructor for class
    def __del__(self):
        #destructor for the scheduler class. This will save the existing queue data to a file for recovery next time the class is instantiated.
        self._save_queue_data()
        self.trace_log.info("DEL")

    #Function to create loggers for the scheduler class. 
    def _create_loggers(self):
        #2 logers are created, one to keep track of the stats of the DB so the size can be 
        #monitored over time and one to keep track of any error which may occur during operation

        '''---Need to find a logical way to decide how large these logs are allowed to be---'''
        #Make sure that the logs directory exists, if not, make it
        if not os.path.isdir(self.log_path): 
            os.mkdir(self.log_path)

        #Set up stats logger
        stats_logname = f"{__name__}_stats"
        self.stats_log = logging.getLogger(stats_logname)
        self.stats_log.setLevel("INFO")
        stats_file_handler = RotatingFileHandler(os.path.join(self.log_path,f"{stats_logname}.log"), maxBytes=5000000, backupCount=3)
        stats_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.stats_log.addHandler(stats_file_handler)

        #Set up scheduler log
        sched_logname = f"{__name__}_sched"
        self.sched_log = logging.getLogger(sched_logname)
        self.sched_log.setLevel("INFO")
        sched_log_file_handler = RotatingFileHandler(os.path.join(self.log_path,f"{sched_logname}.log"), maxBytes=5000000, backupCount=3)
        sched_log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.sched_log.addHandler(sched_log_file_handler)

        #set up tracepoint logger
        trace_logname = f"{__name__}_trace"
        self.trace_log = logging.getLogger(trace_logname)
        self.trace_log.setLevel("INFO")
        trace_log_file_handler = RotatingFileHandler(os.path.join(self.log_path,f"{trace_logname}.log"), maxBytes=5000000, backupCount=3)
        trace_log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.trace_log.addHandler(trace_log_file_handler)

        #set up error logger
        err_logname = f"{__name__}_err"
        self.err_log = logging.getLogger(err_logname)
        self.err_log.setLevel("INFO")
        err_log_file_handler = RotatingFileHandler(os.path.join(self.log_path,f"{err_logname}.log"), maxBytes=5000000, backupCount=3)
        err_log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self.err_log.addHandler(err_log_file_handler)

    def _save_queue_data(self):
        #Sending queue and request rates to a file so that they can be loaded next time the class is instantiated.
        with open(self.scheduler_filename, 'wb') as scheduler_file:
            q_status = self._queue_data(self.cmd_q, self.schedule_rates)
            pickle.dump(q_status, scheduler_file)

    #function to make sure valid queue is in the scheduler before execution begins
    def create_queue(self):
        #Load in queue data from a file if it exists, otherwise create a default queue.
        if not os.path.isfile(self.scheduler_filename):
            print("Cant load schedule file, setting default")
            self.err_log.warning(f"1: {self.scheduler_filename}")
            self._create_default_queue()
        
        #Load data from file and make sure it is valid
        else:
            self._load_queue_data()
            self._validate_queue()

    #load queue object from pickle file and validate it
    def _load_queue_data(self):
        #read queue data from file and set the rates according to that 
        with open (self.scheduler_filename, 'rb') as scheduler_file:
            saved_q_data = pickle.load(scheduler_file)
        
            #set the queue and rates from the saved data
            self.schedule_rates = saved_q_data.rates
            self.cmd_q = saved_q_data.queue

    #Function to make sure items in the queue are valid
    def _validate_queue(self):

        #Set up objects for tracking what is expected and what is still valid
        queue_items = set(self.known_leagues).union(set(self.background))
        remaining_items = set(queue_items)

        #Go through cmd_q, if any items have invalid entries or are duplicates then turn them into None
        for i, each in enumerate(self.cmd_q):
            
            #Queue item {each} is not a tuple
            if not isinstance(each, tuple):
                self.err_log.warning(f"01: {each}")
                self.cmd_q[i] = None
                continue
            
            #Queue item must have length 2
            if len(each) != 2:
                self.err_log.warning(f"02: {each}")
                self.cmd_q[i] = None
                continue
            
            #Queue item must have a datetime as the first element
            if not isinstance(each[0], datetime):
                self.err_log.warning(f"03: {each}")
                self.cmd_q[i] = None
                continue
            
            cmd_type = each[1]

            #Queue item must have known command type
            if cmd_type not in queue_items:
                self.err_log.warning(f"04: {each}")
                self.cmd_q[i] = None
                continue

            #Queue item must not be a duplicate
            if cmd_type not in remaining_items:
                self.err_log.warning(f"05: {each}")
                self.cmd_q[i] = None
                continue
            
            #Check how far away until the next time the command is to be executed
            time_to_exec = each[0] - datetime.now(timezone.utc)
            sec_to_exec = time_to_exec.total_seconds()

            #make sure the scheduled time and request rates are both valid, if not turn the item into None
            if cmd_type in self.known_leagues:

                #if schedule rate is not valid then set to None
                if self.schedule_rates[cmd_type] > self.min_req_rate or self.schedule_rates[cmd_type] < self.max_req_rate:
                    self.err_log.warning(f"07: {each}")
                    self.cmd_q[i] = None
                    continue

                #Next scheduled time for this command is not valid, then reschedule based on polling rate
                if sec_to_exec > self.min_req_rate:
                    self.err_log.warning(f"06: {each}")
                    self.cmd_q[i][0] = datetime.now(timezone.utc) + timedelta(seconds=self.schedule_rates[cmd_type])

            elif cmd_type in self.background:

                #Since this will only ever poll at constant rate, just set it, who cares what was in the file                
                self.schedule_rates[cmd_type] = self.background[cmd_type]

                #If next scheduled time is invalid, then just change it to be valid!
                if sec_to_exec > self.background[cmd_type]:
                    self.err_log.warning(f"08: {each}")
                    self.cmd_q[i][0] = datetime.now(timezone.utc) + timedelta(seconds=self.schedule_rates[cmd_type])
            
            #If we get here, then we know it was legit and remove from remaining_items
            remaining_items.remove(cmd_type)

        #Clear out any None items from the list
        for i in reversed(range(len(self.cmd_q))):
            if self.cmd_q[i] is None: del self.cmd_q[i]
        
        #log items that need to be added to the q
        if len(remaining_items) > 0:
            self.err_log.warning(f"7: {', '.join(cmd for cmd in remaining_items)[:-1]}")
        
        #If there are any items missing, add them to the queue with default rates
        for cmd in remaining_items:

            #If command is added schedule to execute right away
            self.cmd_q.insert(0,(datetime.now(timezone.utc), cmd))
            
            #Add correct schedule rate for the new thing
            if cmd in self.known_leagues:
                self.schedule_rates[cmd] = self.default_req_rate
            else:
                self.schedule_rates[cmd] = self.background[cmd]

        #sanity check making sure q is sorted before beginning execution
        self.cmd_q.sort()

        return True
    
    #Create queue using all of the default rates for the commands
    def _create_default_queue(self):
        
        self.cmd_q = list()
        for league in self.known_leagues:
            self.cmd_q.append((datetime.now(timezone.utc), league))
            self.schedule_rates[league] = self.default_req_rate
        for cmd, rate in self.background:
            self.schedule_rates[cmd] = rate

    #Function to stop the scheduler loop. 
    def stop_scheduler(self):
        #This will set the stop flag to true and then wait for the loop to finish next time it is able. Function
        #can be called by the user to stop the scheduler loop gracefully. Function also returns max time the loop will sleep for so caller can know 
        #how long to wait
        print("Stopping scheduler loop...")
        self.trace_log.info(f"0")
        self._stop_loop = True
        return self.loop_wakeup_time

    #Main function which will be called by the user to run the scheduler. This handles the runtime the user specifies.
    def run_scheduler(self, runtime_mins = 0):

        #If runtime is negative, then nothing to do, raise an error
        if runtime_mins < 0:
            self.err_log.error(f"1: {runtime_mins}")
            raise ValueError("Runtime minutes must be a non-negative number.")
        
        self.trace_log.info(f"0: {runtime_mins}")
        start_time = datetime.now()

        #If runtime is set to some number of mins, then start a thread to run the scheduler loop and wait for that many minutes before stopping the loop
        if runtime_mins > 0:
            self.trace_log.info(f"00: mins={runtime_mins}")
            try:
                action_loop = threading.Thread(target=self._schedule_loop, args=())
                action_loop.start()

                #Sleep program for 2x loop wakeup time while the loop is meant to be running. This gives this thread the ability to wake up and respond
                #to exceptions being raised rather than just let the program hang until the runtime expires
                num_loops = runtime_mins*60/self.loop_wakeup_time/2
                for _ in range(int(num_loops)): time.sleep(2*self.loop_wakeup_time)

            except KeyboardInterrupt:
                #User input stopping loop before timeout
                self.trace_log.info(f"01: tme={(datetime.now()-start_time)/60} - tot={runtime_mins}")

            #stopping scheduler gently and rejoining child thread 
            self.stop_scheduler()
            action_loop.join(timeout = self.loop_wakeup_time+1)
            
            #If child doesn't rejoin in reasonable time, then kill the whole thing
            if action_loop.is_alive():
                self.err_log.critical(f"1")
                exit("Houston, we have a problem! Scheduler did not stop in time. Exiting.")
        
        #If runtime is 0, then just run the loop forever until program exits or user stops it. This does not need a loop to check itself since this
        #is just run in a single thread
        else:

            self.trace_log.info("0000")
            try:
                self._schedule_loop()
            except KeyboardInterrupt:
                #User can stop the loop with ctrl+c, this catches that and stops things gracefully so that everything can be saved correctly
                print("User stopped loop execution")
                self.trace_log.info(f"01: tme={(datetime.now()-start_time)/60} - tot={runtime_mins}")
            
            self.stop_scheduler()

        return True
        
    #Funtion which facilitates getting data from PrizePicks and into the DB and making sure errors are reported accordingly
    def _scrape_prizepicks_data(self, league):
        
        #Make call to the prizepicks API to get the data
        try:
            scrape_data = web_scraper.get_prizepicks(league, self._db_obj)

        #Make sure any excepton caught is in the debug_exc wrapper
        except Exception as e:
            if isinstance(e, debug_exc):
                #Not sure if I need to log this here or not, leaving out for now self.err_log.critical(f"1: lgnum={league}")
                raise e
            self.err_log.critical(f"1: lgnum={league}")
            raise debug_exc(e, "1", {"lg":league}, "SCHEDULER")

        #Log the request
        self.trace_log.info(f"0: lg={league} api={scrape_data[2]}")

        #Send the webpage data to the parser
        webpage = scrape_data[0]
        scrape_id = scrape_data[1]
        
        #Parse the api data collected from the internet
        try:
            wp_data = my_parser.parse_webpage(webpage, self._db_obj)

        #Make sure any excepton caught is in the debug_exc wrapper
        except Exception as e:
            self._db_obj.post_scrape_error(scrape_id, "2")
            if isinstance(e, debug_exc):
                #Not sure if I need to log this here or not, leaving out for now self.err_log.critical(f"2: lgnum={league} - scrid={scrape_id}")
                raise e
            self.err_log.critical(f"2: lgnum={league} - scrid={scrape_id}")
            raise debug_exc(e, "2", {"lg":league, "scrid":scrape_id, "wp":webpage}, "SCHEDULER")

        try:
            self._db_obj.send_to_sql(wp_data, scrape_id)
        
        #Make sure any excepton caught is in the debug_exc wrapper
        except Exception as e:
            self._db_obj.post_scrape_error(scrape_id, "3")
            if isinstance(e, debug_exc):
                #Not sure if I need to log this here or not, leaving out for now self.err_log.critical(f"3: lgnum={league} - scrid={scrape_id}")
                raise e
            self.err_log.critical(f"3: lgnum={league} - scrid={scrape_id}")
            raise debug_exc(e, "3", {"lg":league, "scrid":scrape_id, "wp":webpage}, "SCHEDULER")
        
        return wp_data    

    #Update request frequency for a certain command based on when the next game for that league is
    def _update_req_freq(self, cmd_type, game_data):
        #Takes a look at when the next game for a specific league is and schedules when the next time it should be scheduled is
        #The assumption made in the design of this function is that as a player gets closer to gametime, their spread is more likely to change
        #This function will look at both time since the game was created and time until the game is supposed to start and decide frequency based on the
        #event closest in time (in future or past)

        #None can indicate 2 things: 1 that something went wrong and no data was parsed or 2 that there are in fact no upcoming games and the season
        #is over or no bets are available.
            #So not to overcompensate for the case of #1, will double the refresh time
        '''There should be something added here, None is different than bad status and the scheduling logic should be different for those cases'''
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

        #over one month away, just check once a day
        if sec_to_nxt_gm > FOUR_WKS:
            self.schedule_rates[cmd_type] = self.min_req_rate 

        #4-1 week away
        elif sec_to_nxt_gm > ONE_WK:
            self.schedule_rates[cmd_type] = ONE_HOUR

        #7-4 days away
        elif sec_to_nxt_gm > FOUR_DAYS:
            self.schedule_rates[cmd_type] = THIRTY_MINS

        #4-1 day away
        elif sec_to_nxt_gm > ONE_DAY:
            self.schedule_rates[cmd_type] = FIFTEEN_MINS

        #24-6 hrs away
        elif sec_to_nxt_gm > SIX_HOURS:
            self.schedule_rates[cmd_type] = FIVE_MINS

        #6-3 hrs away
        elif sec_to_nxt_gm > THREE_HOURS:
            self.schedule_rates[cmd_type] = TWO_MINS

        #3-0 hrs away
        elif sec_to_nxt_gm > 0:
            self.schedule_rates[cmd_type] = self.max_req_rate
        
        #Negative time should not be possible, this needs to be checked! Setting to default 
        else:
            #Time to next game is negative, that should not be possible, logging it and resetting to default
            self.schedule_rates[cmd_type] = self.default_req_rate
            return (1, cmd_type, next_game, sec_to_nxt_gm)
        
        return True

    #update queue once a command has been executed and make adjustments to scheduler as-needed
    def _update_queue(self, data):
        
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

        if data is not None and data not in self.background:
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
    
    #Function to move stable data from the more dynamic tables to archive tables after they are expected to quit changing
    def archive_table_data(self):

        self._db_obj.move_to_archive()

    #Function to log current status of the queue and how long the loop is going to sleep for
    def _log_q_status(self, sleep_time = None):
        q_msg = "curq: "
        for sch,cmd in self.cmd_q:
            q_msg += f"{cmd}:{sch.astimezone().isoformat()}:{self.schedule_rates[cmd]}\t"
        self.sched_log.info(f"\t{q_msg[:-1]}")

        if sleep_time is not None:
            slp_msg = f"slp: {sleep_time}sec"
            self.sched_log.info(slp_msg)

    def _schedule_loop(self):
        #this is the loop which will schedule the commands to be executed. This will run until the _stop_loop flag is set to true.        

        self._stop_loop = False
        min_time_to_wait = FIVE_SEC #Only poll so often to avoid spamming the API with requests
        
        #objects to keep track of how many error pop up and for which actions
        consec_errs = 0
        type_errs = {cmd: 0 for cmd in self.known_leagues + list(self.background)}

        #Starting scheduler loop
        self.trace_log.debug("0")
        while True:

            #Check if loop is stopped by parent thread
            if self._stop_loop:
                self.trace_log.info("00")
                break

            #Checking to see if it is time to execute the next command in the queue
            #execute next command if it is scheduled to be done before the next time the loop is supposed to wake up
            nxt_cmd = self.cmd_q[0]
            my_delta = nxt_cmd[0] - datetime.now(timezone.utc)
            sec_to_exec = my_delta.total_seconds()
            data = None
            exec_cmd = sec_to_exec < (self.loop_wakeup_time/2)

            #execute command if it is time
            if exec_cmd:

                cmd_type = nxt_cmd[1]
                print(f"Executing cmd: {cmd_type}")
            
                #Get stats on db size
                if cmd_type == 'sts':
                    self._get_db_stats()

                #Dump mysql backup
                elif cmd_type == 'bu':
                    self._create_mysql_backup()

                #move dynamic data from standard tables to archive tables
                elif cmd_type == 'archive':
                    self.archive_table_data()
                
                #if not dump scheduler command, then need to scrape prizepicks for data
                elif cmd_type != 'dmp_sch':
                    try:
                        #Make API call to get data for a league
                        data = self._scrape_prizepicks_data(cmd_type)
                        
                        #reset error counters if nothing went wrong
                        consec_errs = 0
                        type_errs[cmd_type] = 0

                    #Rather than put all the handling code of all the exceptions in here, just do it all in a fucntion
                    except debug_exc as dbe:
                        self._dbe_handler(dbe, cmd_type, type_errs, consec_errs)
                        continue

                    #If raises exception not in dbe_exc then wrap it in that exception and raise it
                    except Exception as e:
                        raise debug_exc(e, "2", {"cmd":nxt_cmd}, "SCHEDULER")                 
                
                #Reschedule the command that just executed
                self._update_queue(data)

                #check to dump scheduler after it has been re-queued so that the first command executed after restart is not always a schedule dump again
                if cmd_type == 'dmp_sch':
                    self._save_queue_data()

            #If woken up and nothing to do, then go right on back to sleep
            else:
                print("Sleep more")
                self.trace_log.debug("00")
            
            #Tell the loop to sleep until either the next wakeup time or the next command execution time.
            #I do put a limit on here that the loop will not sleep for less than 5 seconds, to avoid spamming the API or more than 15 seconds to avoid
            # situation where the loop cannot be cancelled by the caller.
            sleep_time = min( self.loop_wakeup_time,max( min_time_to_wait,sec_to_exec ) )
            
            #To avoid spam, only log q status if something has been executed
            if exec_cmd: self._log_q_status(sleep_time)
            
            try:
                time.sleep(sleep_time)
            except KeyboardInterrupt as e:
                self._stop_loop = True
                raise e

        #If loop is gracefully broken out of, then reset the stop flag so it can be restarted without issue if needed
        self._stop_loop = False
        return True
    
    #Function to handle and track db-realted errors
    '''---Still much work to be done here, but most of the erros are already fixed elsewhere so not urgent to fic this---'''
    def _dbe_handler(self, dbe, cmd_type, type_errs, consec_errs):
        '''
        Eventually, if the problem is just related to the single cmd_type then we need to just evict it from the q or set it to lowest
        polling rate so that it doesnt keep clogging us up and doesnt stop everything else if that is all working properly
        '''
        
        reschedule = True   #Sometimes statndard reschedule is not wanted, so this control the case where we don't want to do that
        dump_any = True     #Set to True to take snapshot on every error, set to false if not

        #If the error is a timeout in getting the prizepicks api, it likely just means that internet connection was bad for a bit, so 
        #just going to wait 5 min and try again
        '''---Eventually will need to add support for this I think since the curl commands do time out from time to time---'''
        '''
        if isinstance(dbe.exc, Timeout):
            self._handle_timeout(cmd_type, type_errs, dbe, consec_errs)
            reschedule = False
            dump_any = False
        '''

        print(f"Found exception while scraping pp. Logging this error. Counts:\n{consec_errs}\n{type_errs}")
        consec_errs += 1
        type_errs[cmd_type] += 1
        self._cmd_err_handler(dbe, cmd_type, type_errs, consec_errs, dump_any)

        if reschedule is True:
            self._update_queue(None)
    
    #Function to hanle logging and atttempt recovery from timeouts
    def _handle_timeout(self, cmd_type, type_errs, dbe, consec_errs):
        
        #print to the console and all the relevant logs that the timeout occured, which command timed out and when it is rescheduled for
        print(f"Found timeout in getting prizepicks API data, watiting 5 min to make next request. Counts:\n{consec_errs}\n{type_errs}")
        new_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        err_msg = f'1: cmd={cmd_type} - nt={new_time.strftime("%Y-%m-%d %H:%M:%S")}'
        self.sched_log.error(err_msg)
        self.trace_log.error(err_msg)
        self.err_log.error(err_msg)

        #update the q so that the next command is not executed for another 5 min
        self.cmd_q[0][0] = new_time

        #update consec error counts and handle the error
        consec_errs += 1
        type_errs[cmd_type] += 1
        self._cmd_err_handler(dbe, cmd_type, type_errs, consec_errs, dump = False)
    
    #function to log all debug saved for exceptions from process of making API call to loading in DB
    def _cmd_err_handler(self, dbe, ct, te, ce, dump = True):
        if dump is True:
            fn = dbe.dump()
        else:
            fn = None

        if ce > 3 or te[ct] > 3:
            if dump is False :
                fn = dbe.dump()
            self.err_log.error(f"2222: ce={ce} - te={ct}:{te[ct]} - fn={fn}")
            raise RuntimeError(f"Too many failed commands in a row. Last command executed = {ct}")
        self.err_log.error(f"22: cmd={ct} - fn={fn}")

    #Function to get the size of the tables in the db and log them
    def _get_db_stats(self):
        #Function asked the db object what it's stats are, then logs them
        db_stats = self._db_obj.get_stats()

        #Construct log message from the db stats retruned from the object
        mystr = "tbszs(mb): "
        for name, size in db_stats: mystr += f"{name}:{size}\t"

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

    #Function to take a json object and send it to a text file - usually for debugging
    def _json_snap(self, prefix, data):
        raise NotImplementedError
        #correlate the error to the dump
        fn = self._create_snap_fn(prefix)
        with open(fn,"w") as json_file:
            json.dump(data, json_file, indent=4)
        self.trace_log.debug(f"0: fn={fn}")
        return fn

    def _exc_snap(self, prefix, e, traceback):
        raise NotImplementedError
        #Function to take in an exception object and send it to a text file for logging and review purposes
        fn = self._create_snap_fn(prefix)
        with open(fn,"w") as f:
            f.write(f"{e.__class__.__name__}\n")
            f.write(f"{e}\n")
            f.write(traceback) # Get the formatted traceback string

        self.trace_log.debug(f"0: fn={fn}")
        return fn
    
    #Function Executed when mysql backup is time to be created
    def _create_mysql_backup(self):
        #crates a deamon thread and calls the prizepicks_db create_sql_backup function. Since this function will take a long time, we don't wait
        # for it to finish, the daemon thread will run in paralell until it is completed since no need to block all other execution of the main
        # thread for this

        #Check to make sure there is not already a backup thread alive, if there is, then don't start a new one and log an error
        if self._bu_thread.is_alive():
            self.err_log.warning("01: CANNOT CREATE EXTRA BU THREAD")
            return 1
        
        self._bu_thread = Thread(target = self._db_obj.create_sql_backup, args=(True,), daemon=True)
        self._bu_thread.start()
    
    #class to hold all the relevant queue data from scheduler class when it is destructed. this way the data persists even if the class is deleted
    class _queue_data:
        queue = list()
        rates = dict()

        def __init__(self, caller_queue, caller_rates):
            self.queue = caller_queue
            self.rates = caller_rates

#Main function which creates scheduler object and runs it
if __name__ == "__main__":

    user_input = input("Booting up prizepicks scraper, 'y' will begin the program, anything else will exit\n")
    if user_input.upper() != 'Y':
        exit("Not starting anything. Exiting the program.")

    s = prizepicks_scheduler()
    try:
        s.run_scheduler()

    except Exception as e:
        '''---Need to add logging to this in order to catch any undexpected stuff---'''
        with open(os.path.join(os.path.dirname(__file__),"logs",f"killer_error_log{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.err"), "a") as f:
            # traceback.format_exc() returns the full traceback as a string
            f.write("--- New Error ---\n")
            f.write(traceback.format_exc())
            f.write("\n")
    
    del s
    '''---temporary add---
    command = ["sudo", "-S", "shutdown", "-h", "now"]

    # Start the process and send the password followed by a newline
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(input=password + "\n")'''
