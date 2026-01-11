import mysql.connector
import utils
from datetime import datetime, timezone
from utils import parsed_data, debug_exc
from my_logs import log_perf
import os
import logging
from logging.handlers import RotatingFileHandler
import traceback
import subprocess
from pathlib import Path

#Helper class to help with holding data for many to many relationships. To compare and decide what needs to be updated
class one_to_many:
    
    base_id = int
    target_ids = set()
    version = int
    islatest = bool

    def __init__(self, b_id, ver, latest, t_id_set):
        self.base_id = b_id
        self.target_ids = t_id_set
        self.version = ver
        self.islatest = latest

class prizepicks_db:

    SQL_RESERVED_WORDS = {
        "type",
        "description",
        "rank",
        "status",
        "time"
    }
    PROJECTION_TIME_SERIES = {
        "line_score",
        "trending_count",
        "rank"
    }
    INCLUDED_TIME_SERIES = {
        'team':[],
        'new_player':[],
        'stat_type':[],
        'league':[],
        'game':[],
        'projection_type':[]
    }
    _MY_TABLES = [
        'projection',
        'team',
        'new_player',
        'stat_type',
        'league',
        'game',
        'projection_type'
    ]
    _sql_conn = None
    _sql_cursor = None
    _external_data_names = dict()
    _log = None
    _db_name = None
    _archive_path = None
    _log_path = None
    _config = None
    _dt_frmt = "%Y_%m_%d_%H_%M_%S"

    def __init__(self):

        self._config = utils.get_secret("mysql")
        self._create_log()
        self._set_archive_path()   
        self.compare_sql_schema()
        self._sql_conn = self._create_db_connection()
        self._sql_cursor = self._sql_conn.cursor()
        self._set_external_data_names()        
     
    #Function to set _config['archive'] and make sure that the path it points to exists
    def _set_archive_path(self):
        #if archive path is given, make sure it exists
        if self._config.get('archive') is not None:
            #create and store archive path as path object
            self._archive_path = os.path.abspath(self._config['archive'])
            self._log.info(f"0: {self._config['archive']}")
        else:
            #if no archive path given, use the logs directory to store archives
            self._archive_path = self._log_path
            self._log.info(f"00: {self._config['archive']}")

        #check to make sure the final path for the archive exists, if not, then throw exception
        if os.path.exists(self._config['archive']) is False:
            self._log.critical(f"1: {self._config['archive']}")
            raise debug_exc( FileNotFoundError, "1", {"arch_path":self._config['archive']}, "PPDB")

    #Create a log for this class
    def _create_log(self):
        
        #create path for log files to go
        self._log_path = os.path.join(os.path.dirname(__file__),"logs")
        file_handler_path = os.path.join(self._log_path,".log")

        if not os.path.isdir(self._log_path): 
            os.mkdir(self._log_path)

        #Set up stats logger
        stats_logname = f"{__name__}_stats"
        self._log = logging.getLogger(stats_logname)
        self._log.setLevel("INFO")
        stats_file_handler = RotatingFileHandler(file_handler_path, maxBytes=5000000, backupCount=1)
        stats_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self._log.addHandler(stats_file_handler)

    #Run to concisely get all the names of all the data names for a given data type parsed from the prizepicks api
    def _set_external_data_names(self):
        #This function runs through all the tables of the db, which are hard-coded into the _MY_TABLES member variale
        #And runs through all the tables in the db which could contain data about them and stores it in a dict which
        #Is stored as a member variable

        for table_name in self._MY_TABLES:
            
            '''Is there a way to combine these two read queries?'''
            #Get the info about all the columns of the target table, and just pick out the names
            self._sql_cursor.execute(f"SHOW COLUMNS FROM {table_name};")
            cols_list = self._sql_cursor.fetchall()
            table_cols = [each[0] for each in cols_list]
            #Some names are modifies to avoid mySQL reserved words, so this undoes that modification
            data_names = self._remove_mysql_prefix(table_cols)

            #Pull the expected timeseries names from the member valiables above
            if table_name == 'projection':
                ts_names = list(self.PROJECTION_TIME_SERIES)
            else:
                ts_names = self.INCLUDED_TIME_SERIES[table_name]

            #Add the names of both the target table and the timeseries tables to save
            self._external_data_names[table_name] = data_names + ts_names

    def get_data_to_parse(self):
        #Don't want caller messing with the member variable directly, so this fuctions allows a caller to a
        #copy of those names
        return self._external_data_names.copy()

    def _create_db_connection(self, db_name = None, host_name = None, user_name = None, user_password = None):      
        #Function to create a connection to the local mySQL database. Credentials can be passed in or they default to None and if host_name is left as None
        #then the root_login() function will get the root login data form a file somewhere on the computer

        #If no db name is passed in, then they are all loaded in from secrets file
        if db_name is None:
            creds = self._config
            db_name = creds['db_name']
            host_name = creds['hn']
            user_name = creds['un']
            user_password = creds['pw']

        print(f"Connecting to '{db_name}' DB")

        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )

        #MySQL Database connection successful
        self._log.info(f"0: db={db_name}")
        return connection

    #Function called by app manager to send the parsed data to the local mySQL database
    def send_to_sql(self, parsed_data_obj, scrape_id):
        
        if not isinstance(parsed_data_obj, parsed_data):
            self._log.warning(f"1: type={type(parsed_data_obj)}")
            return 1
        
        #Sends values parsed into the projection table
        
        #No data to send to the DB, returning since there is nothing to do")
        if len(parsed_data_obj.data_values) == 0:
            self._log.info(f"0000")
            return True
        
        self._send_to_projection_table(parsed_data_obj.data_order, parsed_data_obj.data_values, scrape_id)
        self._send_included_data(parsed_data_obj.included_tag_values, scrape_id)
        #Commits changes made during above functions
        self._sql_conn.commit()
        return True
    
    #Function takes in the headers of the incoming data and maps them to the order which they appear in the mysql table 
    '''
    For this section, I wonder if rather than just sending everything in in the prerfectly correct order it would be easier to just tell the db
    the column name order that the info will come in. May clean up the code a bit here.
    '''
    @log_perf
    def _create_col_ordering(self, headers, table): 
        mysql_cols = list()
        mysql_map = list()
        dt_indexes = list()
        translated_headers = list()

        self._sql_cursor.execute(f"SHOW COLUMNS FROM {table};")
        cols_list = self._sql_cursor.fetchall()
        mysql_cols = [each[0] for each in cols_list]

        #This list will be used to map which index of the incoming headers corresponds to the index of the mysql columns
        mysql_map = [None]*len(mysql_cols)

        #Some cols are saved as datetimes. Keeping track of which cols in table are dts is important when checking for equality later
        for i, v in enumerate(cols_list):
            if v[1] == "datetime":
                dt_indexes.append(i)

        #Take the incoming header list and make sure all names are translated to be mysql-compatible
        for i,header in enumerate(headers):
            #ignore anything that is a timeseries since that will not show up in the projections table
            if header in self.PROJECTION_TIME_SERIES:
                continue
            
            #Add 'my_' to the front of the mysql reserved words so that all column names
            if header in self.SQL_RESERVED_WORDS: 
                header = f"my_{header}"
            translated_headers.append(header)
            
            #Align the incoming headers with how they appear in the db
            try:
                col_num = mysql_cols.index(header)
                mysql_map[col_num] = i
            except ValueError:
                self._log.warning(f"01: unexhdr={header}")
                continue
        
        return (mysql_map, dt_indexes, translated_headers)

    #Function to get existing data from the given table name and all the data which is from the passed in ids
    @log_perf
    def _get_existing_data(self, table, id_list):
        
        #Pull in all incoming row ids so db can be queried for existing rows
        my_len = len(id_list)
        if my_len == 0:
            #No data to add for {table}. Returning empty list
            self._log.info(f"0000")
            return []
    
        #build SQL query to get existing data from the db for the ids to compare with
        base_sql = f"SELECT * FROM {table} "
        where_clause = "" if id_list is None else f"WHERE ID in ({','.join([str(data_id) for data_id in id_list])})"
        sql_query = base_sql + where_clause
        return self.read_query(sql_query)

    #Function to create timeseries entires for each entry in the incoming row if it exists
    def _add_timeseries(self, hdr_order, incoming_row, row_id, scrape_id, last_values):
    #If timeseries data does exist in the incoming row, then the row which must be added to the
    #mysql is returned

        timeseries_list = list()
        for timeseries in self.PROJECTION_TIME_SERIES:
            #Not all timeseries data is always guarunteed, so this check to make sure that the timeseries data actually exists before trying to add anything. 
            #If it does not exist then just skip it, that's ok.
            '''Probably faster way to do this somehow rather than look for the same indexes each time'''
            try:
                ts_ind = hdr_order.index(timeseries)
            except ValueError:
                continue

            kw = self._create_keyword([row_id,timeseries])

            if incoming_row[ts_ind] is not None:
                last_value = last_values.get(kw)
                new_value = incoming_row[ts_ind]

                if last_value is None:
                    #If there is not data for last value in the DB then it can be added in there
                    last_values[kw] = new_value
                    timeseries_list.append([row_id, timeseries, incoming_row[ts_ind], scrape_id])

                elif last_value[2] != new_value:
                    #if value has changed then add it to the timeseries list
                    timeseries_list.append([row_id, timeseries, incoming_row[ts_ind], scrape_id])
                else:
                    #If the data already exists then no need to add it again
                    pass

            else:
                #if timeseries data does not exist in the incoming row, then just skip it
                pass
 
        return timeseries_list

    #This fucntion goes through each of the items of two existing and incoming data rows and compares them. If any differences then
    #They are added to the change list in the formate I want to store in the db and returned to the caller
    def _create_changes(self, num_cols, mapping, translated_headers, existing_row, temp_row, row_id, scrape_id, change_list):
        change_list = list()
        for i in range(num_cols):
            #If a value has changed, then add it to the change list and mark that a change has been made. This change will be logged in the appropriate change_history table
            if existing_row[i] != temp_row[i]:
                change_list.append([row_id, translated_headers[mapping[i]], existing_row[i], scrape_id])
        
        return change_list
    
    #function to pull in all the last timeseries values for the passed in projection ids
    @log_perf
    def _get_last_values(self, proj_ids):

        #Pull in all the data from the DB for the interested timeseries and turn it into a dict
        my_q =f"""
        SELECT * 
        FROM projection_timeseries 
        WHERE projection_id in ({','.join([str(proj_id) for proj_id in proj_ids])}) 
        ORDER BY parsenum DESC;
        """
        self._log.debug(my_q)
        all_ts = self.read_query(my_q)
        #create dict to see what the latest value for a given projection is
        ts_dict = dict()
        for data_point in all_ts:
            kw = self._create_keyword([data_point[0],data_point[1]])

            if kw not in ts_dict:
                ts_dict[kw] = data_point

        return ts_dict

    @log_perf
    def _send_to_projection_table( self, headers, data, scrape_id):
        #Function which will send passed in data into the 'data' table of the local mySQL database
        #Argumetns are:
        #    headers - a list of names of the columns of the target table in order for how they apprear in the data
         
        #    data - a list of lists where each sub-list is the list of data that is going into the database. The data point at each index is
        #        described by that same index of 'headers' list

        #    scrape_id - the id of the scrape that this data is coming from.
    
        mapping = list()
        dts = list()
        translated_headers = list()
        table = 'projection'
        id_index = headers.index("id")

        #tuple of all the projection ids of the incoming data
        new_proj_ids = tuple(values[id_index] for values in data)
        #Pull into memory any data already be in the db to compare/update against
        existing_data = self._get_existing_data(table, new_proj_ids)

        #Call function to map the incoming data to the order that the db requires
        mapping, dts, translated_headers = self._create_col_ordering(headers, table)
 
        
        #Create dictionary where the key is the row id and the value is the row of existing data in the mysql db. This will be used to 
        #check for if any rows need to be updated
        data_dict = dict()
        for row in existing_data:
            data_dict[row[id_index]] = row

        #Create dict to keep track of the latest values of the timeseries parsed from the projection data. This will dictate whether a new data point 
        # hould be added to a timeseries or not
        last_values = self._get_last_values(new_proj_ids)

        #loop through each of the headers and determine which are timeseries so that they can be handled separatley from the items which are not 
        # expected to change
        ts_hdr_inds = dict()

        for ts in self.PROJECTION_TIME_SERIES:
            try:
                ts_hdr_inds[ts] = headers.index(ts)
            except ValueError:
                #Cant find index of {ts}, unexpected, but not critical
                self._log.warning(f"01: tsntfnd={ts}")
                ts_hdr_inds[ts] = None

        #Call function that loops through each of the incoming data rows to determine what changes need to be made in the db. Any changes that need to be made, the 
        #necessary data to do that is added to the insert, update, or timeseries list as apropriate. These lists are then executed in batches into the
        #db to make it fast Rather than calculate the index for each of the timeseries iteration of loop, do it once before we get into the loop. Also
        #including stat_type index as well since I need that too
        insert_list, change_list, update_list, timeseries_list = self._loop_data(data, id_index, mapping, dts, data_dict, translated_headers, scrape_id, headers, last_values)

        #Function which makes batch requests for the 3 tables to be updated
        self._add_new_lines(insert_list, change_list, update_list, table, timeseries_list)
            
    #This loops through each of the incoming data rows to determine what changes need to be made in the db. Any changes that need to be made, the 
    #necessary data to do that is added to the insert, update, or timeseries list as apropriate. These lists are then executed in batches into the
    #db to make it fast Rather than calculate the index for each of the timeseries iteration of loop, do it once before we get into the loop. Also
    #including stat_type index as well since I need that too
    @log_perf
    def _loop_data(self, data, id_index, mapping, dts, data_dict, translated_headers, scrape_id, headers, last_values):
        
        insert_list = list()
        update_list = list()
        change_list = list()
        timeseries_list = list()
        
        for i,incoming_row in enumerate(data):
            #Map the data from the incoming row into a temp row so that it can be compared against whatever is already in the db in the correct 
            # order/format
            temp_row = list()
            row_id = incoming_row[id_index]
            num_cols = len(mapping)
            
            #Adds incoming data to the temp row in the correct order
            for i in mapping:
                if i is not None:
                    temp_row.append(incoming_row[i])
                else:
                    temp_row.append(None)

            #Converts any datetimes to datetime objects of the same format so their comparison is valid
            for i in dts:
                if isinstance(temp_row[i], str):
                    my_dt = datetime.fromisoformat(temp_row[i])
                    utc_dt = my_dt.astimezone(timezone.utc)
                    temp_row[i] = utc_dt.replace(tzinfo=None)

            ###Beginning comparison and adding necessary data to correct lists to make updates
            
            #If there is nothing already in the DB matching the data id, insert the values straight into the DB
            existing_row = data_dict.get(row_id)
            if existing_row is None:
                insert_list.append(temp_row)
                
            #If the projection is already in the DB, then check to see if anything has changed. If a value has changed, then log it in the 
            #'projection_change_history' table and update the 'projection' table to reflect the new values
            else:
                #Call function to check equality of the incoming vs existing row and return list of any changes
                changes = self._create_changes(num_cols, mapping, translated_headers, existing_row, temp_row, row_id, scrape_id, change_list)

                #If changes are made then add that to the correct data structures to be put in the right places
                if len(changes) > 0:
                    change_list += changes
                    update_list.append(temp_row)

            #Call function to add any timeseries data to the timeseries list if it exists in the incoming row
            timeseries_list += self._add_timeseries(headers, incoming_row, row_id, scrape_id, last_values)

        return insert_list, change_list, update_list, timeseries_list

    @log_perf
    def _add_new_lines(self, my_data_list, data_history_list, update_list, table_name, timeseries_list, row_id_index = 1):
        #Function takes various lists of data all of which needs to be updated in the db, and updates the db with that data

        #Goes through and updates the rows in the target table which have had values changed
        if len(update_list) > 0:
            #To update the existing projection rows in the db, they are first deleted and then replaced by the updated rows

            #Goes through the update list and grabs the ids of the rows that need to be deleted
            delete_ids = [row[row_id_index] for row in update_list]
            
            #add the updated row to my_data_list so that the latest data is inserted into the db
            my_data_list += update_list

            #build SQL query to delete the rows with old data in them
            base_sql = f"DELETE FROM {table_name} "
            where_clause = "" if delete_ids is None else f"WHERE ID in ({','.join([str(x) for x in delete_ids])})"
            delete_query = base_sql + where_clause

            try:
                self._sql_cursor.execute(delete_query)
            except mysql.connector.Error as sql_err:
                #If something goes wrong with delete query, then that is really bad. Stop the program...
                self._log.critical(f"1: qry={delete_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
                raise debug_exc(sql_err, "1", {"qry":delete_query}, "PPDB")

        #Goes through and add in all the latest row data to the target table
        if len(my_data_list) > 0:

            #call function to insert the data list into the table_name
            self._insert_many_rows(table_name, my_data_list)

            #log however many rows were added to which table
            self._log.info(f"0: add={len(my_data_list)} - tbl={table_name}")

        #All of the changes to the projections are tracked. This block adds the changed attributes and values into the table tracking the history of the changes
        if len(data_history_list) > 0:
            
            #Create the SQL query to format and insert the data into the db
            history_alias_list = str()
            for _ in range(len(data_history_list[0])):
                history_alias_list += "%s,"
            history_write_query = f"INSERT INTO {table_name}_change_history VALUES({history_alias_list[:-1]});"
            
            #Execute the SQL query created above
            try:
                self._sql_cursor.executemany(history_write_query, data_history_list)

            except mysql.connector.Error as sql_err:
                self._log.critical(f"3: qry={history_write_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
                raise debug_exc(sql_err, "3", {"qry":history_write_query, "dta_lst":data_history_list}, "PPDB")

            #log however many rows were added to which table
            self._log.info(f"0: add={len(data_history_list)} - tbl={table_name}")
            
        #Some of the projection attributes are expected to change all the time. Rather than keep changing the whole projection record every time, these
        #values are tracked/stored in this timeseries table and the latest values are alwyas inserted in here. This does not check if that value has changed
        #at all, it just adds it no matter what

        if len(timeseries_list) > 0:

            #Create the SQL query to format and insert the data into the db
            ts_alias_string = str()
            for _ in range(len(timeseries_list[0])):
                ts_alias_string += "%s,"
            ts_write_query = f"INSERT INTO {table_name}_timeseries VALUES ({ts_alias_string[:-1]});"

            #Execute the SQL query created above
            try:
                self._sql_cursor.executemany(ts_write_query, timeseries_list)

            except mysql.connector.Error as sql_err:
                self._log.critical(f"4: qry={ts_write_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
                raise debug_exc(sql_err, "4", {"qry":ts_write_query, "dta_lst":timeseries_list}, "PPDB")

            #log however many rows were added to which table
            self._log.info(f"0: add={len(timeseries_list)} - tbl={table_name}")

        return True
    
    def _report_sql_error(self, error, query, rows):
        raise NotImplementedError
        print(f"Query: {query}")
        print(f"ERROR MESSAGE: {error.msg}")
        for row in rows:
            print(row)
        raise Exception("SQL Error found, please review")

    #Function within the class to handle all the reads to the DB
    def read_query(self, query):
        
        try:
            self._sql_cursor.execute(query)
            result = self._sql_cursor.fetchall()
        
        except Exception as e:
            self._log.warning(f"9999: qry={query} - err={e.__class__.__name__} - msg={e.msg} - tb={traceback.format_exc()}")
            raise e
            
        return result

    #Function to remove the prefixes added when data is put into the mysql to avoid reserved words
    def _remove_mysql_prefix(self, name_list):
        '''
        Shitty code that I should just do with list comprehension, but this is easier to read for now
        '''
        clean_list = list()
        for col_name in name_list:
            if len(col_name) > 3 and col_name[:3] == "my_":
                clean_list.append(col_name[3:])
            else:
                clean_list.append(col_name)
        return clean_list

    #Function to post to the db that there was an error parsing the data from a specific api scrape
    def post_scrape_error(self, scrape_id, error):
        update_existing = f"UPDATE scrape_data SET my_status = {error} WHERE id = {scrape_id};"
        self._sql_cursor.execute(update_existing)
        self._sql_conn.commit()

    #function which takes in the required data to define a scrape entry in the db.
    #this function add that the db and returns the id of that new entry
    def create_scrape_id( self, status, leaguenum, timestamp):

        self._sql_cursor.execute(f"INSERT INTO scrape_data (id, my_status, league_num, store_time) VALUES ( NULL, {status},{leaguenum}, '{timestamp}');")
        self._sql_conn.commit()
        scrape_id = self.read_query('SELECT LAST_INSERT_ID();')[0][0]
        return scrape_id
    
    def _send_included_data(self, included_data_dict, scrape_id):
        #Function to send the included data to the db. Since included data spans multiple types and tables, this
        #needs to go through each of the items in the included_data_dict and put the data into the correct table.
        #Each key of the dictionary is the table name that the data is going into, and the values are a single 
        #list of dicts where each dict key is the column name and the value is the value for that column in a given 
        #row.
        for table, data in included_data_dict.items():
            #Loop through each of the tables in the included_data_dict and send the data to the db
            insert_list = list()
            change_list = list()
            update_list = list()
            timeseries_list = list()
            dt_indexes = list()
            col_order = list()

            #get order of columns for the given table and keep track of any datetimes (they need special handling)
            self._sql_cursor.execute(f"SHOW COLUMNS FROM {table};")
            col_info = self._sql_cursor.fetchall()
            for i, col in enumerate(col_info):
                col_order.append(col[0])
                if col[1] == "datetime":
                    dt_indexes.append(i)

            id_index = col_order.index('id') #finding this just in case it changes in the future, it should always be at [0] though            

            #pull in existing data for the db into a dict to compare against and see if any changes need to be made to the db
            incoming_ids = [row['id'] for row in data]

            #build SQL query to delete the rows with old data in them
            base_sql = f"DELETE FROM {table} "
            where_clause = "" if incoming_ids is None else f"WHERE ID in ({','.join([str(x) for x in incoming_ids])})"
            sql_query = base_sql + where_clause
            existing_data = self.read_query(sql_query)
            
            existing_dict = dict()
            for row in existing_data:
                existing_dict[row[id_index]] = row

            #Go through each of the rows in the incoming data and check to see if any changes need to be made
            for incoming_data in data:

                #turn the dict into a list of values in the correct order to be intput to the db
                row_list = [incoming_data[col_name] for col_name in col_order]
                row_list[id_index] = int(row_list[id_index])

                #Convert any datetimes to datetime objects of the same format so their comparison is valid
                for i in dt_indexes:
                    if isinstance(row_list[i], str):
                        my_dt = datetime.fromisoformat(row_list[i])
                        utc_dt = my_dt.astimezone(timezone.utc)
                        row_list[i] = utc_dt.replace(tzinfo=None)

                existing_row = existing_dict.get(row_list[id_index])

                #If the row is new, then it can be added straight into the db insert list
                if existing_row is None:
                    insert_list.append(row_list)
                
                #If row is already in db, then check to see if any changes need to be made
                else:
                    change = False

                    #make any necessary entries to the correlary change_history table
                    for i in range(len(col_order)):
                        if row_list[i] != existing_row[i]:
                            if str(row_list[i]) != str(existing_row[i]):
                                change = True
                                change_list.append([incoming_data['id'], col_order[i], existing_row[i], scrape_id])
                    
                    #Adding the new row to the update list so the old data can be overwritten with the new data for this row
                    if change:
                        update_list.append(row_list)

                #insert timeseries data into correlary timeseries table
                for ts_name in self.INCLUDED_TIME_SERIES[table]:
                    if incoming_data[ts_name] is not None:
                        timeseries_list.append([incoming_data['id'], ts_name, incoming_data[ts_name], scrape_id])   

            self._add_new_lines(insert_list, change_list, update_list, table, timeseries_list, id_index)

    def _build_dict(self, lgnm, nums, start):
        raise NotImplementedError
        self._log.debug(f"0")
        id_list = self.read_query(f"SELECT id FROM scrape_data WHERE league_num = {lgnm} AND my_status = 1 AND is_cleaned = 0 AND id > {start} ORDER BY store_time ASC;")
        pre_dict = dict()
        print("\tGetting parse data from the DB")
        for i in range(nums):

            parse_data = self.read_query(f"SELECT * FROM projection_timeseries WHERE parsenum = {id_list[i][0]}")
            for row in parse_data:

                kn = f"{row[0]}_{row[1]}"
                temp_series = pre_dict.get(kn)
                if temp_series is None:
                    pre_dict[kn] = [row[2]]
                else:
                    '''---To make code back to the way it was, remove this if/else satetmtn'''
                    temp_series.append(row[2])

        return pre_dict

    #Function to standardize creation of keys for dict in cleaning db with proj_id and ts_name
    def _create_keyword(self, row_data):
        if len(row_data) < 2:
            #need to make sure there are tuple long enough to make the keyword before doing it
            self._log.critical(f"1111: invrow={row_data}")
            raise debug_exc(IndexError, "1111", {"invrow":row_data}, "PPDB")
        return f"{row_data[0]}_{row_data[1]}"

    #This is the function which will be called periodically to retrieve stats for the size of the db to be logged over time
    def get_stats(self):
        
        size_query = f"""
        SELECT 
            TABLE_NAME AS `Table`,
            ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS `Size (MB)`
        FROM 
            information_schema.TABLES
        WHERE 
            TABLE_SCHEMA = '{self._db_name}'
        ORDER BY 
            (DATA_LENGTH + INDEX_LENGTH) DESC;
        """
        self._sql_cursor.execute(size_query)
        result = self._sql_cursor.fetchall()
        return result

    #functtion to go through all the lines that have changed in a change object from command line
    def _valid_schema_changes(self, rows):

        #These are the things that the program is going to look for when it decides if the changes in the diff are acceptable or not
        change_allowed = {
            "AUTO_INCREMENT=",
        }

        #get starting line number in comparison
        line_nums = rows[0]

        #lists to hold strings for the actual and expected schema attributes
        actual = []
        expected = []

        #loop through each of the rows to determine if schema differences are ok
        for row in rows[1:]:

            #Assign correct string based on whether they are the sql_schema or the expected_schema
            if row[0] == '<': actual.append(row[2:])
            elif row[0] == '>': expected.append(row[2:])

            #Ignore spacer rows
            elif row == '---': continue

            #If none of the above then compare the lines
            else:

                #Go through the list and first remove all the lines that are either comments or just whitespaces
                for i in reversed(range(len(actual))):
                    if actual[i][:2] == "--":
                        del actual[i]
                    elif len(actual[i].replace(" ","")) == 0:
                        del actual[i]
                for i in reversed(range(len(expected))):
                    if expected[i][:2] == "--":
                        del expected[i]
                    elif len(expected[i].replace(" ","")) == 0:
                        del expected[i]

                #If not the same length, then schema probably different - return false
                if len(actual) != len(expected):
                    return False
                
                #go through all the existing rows and see if they are the same with allowed changes removed
                for i in range(len(actual)):

                    actual_comp = actual[i]
                    expected_comp = expected[i]

                    #Look to see if any allowable changes exist in the row
                    for name in change_allowed:

                        #Check if the alloweable change exists in the row, and if so, where
                        change_a = actual[i].find(name)
                        change_e = expected[i].find(name)

                        #If not found in either line, then check for next one
                        if change_e == -1 and change_a == -1:
                            continue

                        #If an allowable change is found, then remove that part of the row
                        if change_a > -1:
                            delim = actual_comp.find(" ", change_a)
                            actual_comp = actual_comp[:change_a] + actual_comp[delim:]

                        if change_e > -1:
                            delim = expected_comp.find(" ", change_e)
                            expected_comp = expected_comp[:change_e] + expected_comp[delim:]


                    #If these are not the same the change is to be considered unacceptable and raise
                    if actual_comp.replace(" ","") != expected_comp.replace(" ",""):
                        self._log.critical(f"1: lnum={line_nums} exp={expected_comp} act={actual_comp}")
                        raise debug_exc (ValueError("Expected sql schema is not same as actual"), "1", {"lnum":{line_nums}, "exp":{expected_comp}, "act":actual_comp}, "PPDB")

                #once comparison is done, then clear variables and reset the line nums
                actual = []
                expected = []
                line_nums = row
        
    #function to insert many rows into a single table with single statement
    def _insert_many_rows(self, table_name, rows):
        
        #Create the SQL query to format and insert the data into the db
        data_alias_list = str()
        for _ in range(len(rows[0])): data_alias_list += "%s,"
        my_data_write_query = f"INSERT INTO {table_name} VALUES ({data_alias_list[:-1]});"

        #Execute the SQL query created above
        try:
            self._sql_cursor.executemany(my_data_write_query, rows)

        except mysql.connector.Error as sql_err:
            #If something goes wrong with query, then that is really bad. Stop the program...
            self._log.critical(f"2: qry={my_data_write_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
            raise debug_exc(sql_err, "2", {"qry":my_data_write_query, "dta_lst":rows}, "PPDB")

    #Function to compare the expected schema file in the repository with what the schema is of the actual database that is being used
    def compare_sql_schema(self):
    
        #setting up system paths and getting info from config file
        dir_path = os.path.dirname(os.path.abspath(__file__))
        fn = os.path.join(dir_path, self._config['schema_file'])
        sudo = self._config.get("sudo")

        #use commandline tool to dump the mysql schema and compare it to the expected file
        if sudo is not None:
            schema_diff_cmd = f"echo '{sudo}' | sudo -S mysqldump -u {self._config['un']} --password={self._config['pw']} --no-data {self._config['db_name']} | diff - {fn}"
        else:
            schema_diff_cmd = f"sudo mysqldump -u {self._config['un']} --password={self._config['pw']} --no-data {self._config['db_name']} | diff - {fn}"
        
        try:
            result = subprocess.run(schema_diff_cmd, shell=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            # Handle errors if the command returns a non-zero exit code
            print(f"command failed with error code {e.returncode}")
            print(f"Stderr: {e.stderr}")
            self._log.critical(f"1: failed creation of compare object from:{fn}")
            raise debug_exc(e,"1",{"cml":schema_diff_cmd})

        #put ech of the lines that changed into different strings in list go through each of the rows
        #of the diff output and check to see if they are acceptable changes
        rows = result.stdout.splitlines()

        #If there are lines in the change object, check if any of them invalidate the schema
        if len(rows) > 0:
            self._valid_schema_changes(rows)
        
        #if it gets here then we know the schema is valid, return true and set the db_name variable
        self._db_name = self._config['db_name']
        return True

    #Function to move cold data to archive tables for the colder data
    @log_perf
    def move_to_archive(self):

        hot_tables = ['projection'] #List of tables where many changes are expected to be made, stored in smaller tables
        criteria = 6 #number of hours old a game has to be to be eligible for archive

        #Get all the ids of games that started more than critera # of hours ago
        game_id_query = f"SELECT id FROM game WHERE start_time < NOW() - INTERVAL {criteria} HOUR"
        id_list = self.read_query(game_id_query)
        gm2mv = len(id_list)
        self._log.info(f"0: gm2mv={gm2mv} interv={criteria}")

        #if no game ids to move then just return
        if gm2mv == 0: 
            self._log.info("00 msg=no games to move")
            return
        
        '''---Should revisit how many hot tables there are and if all this code really needs to be here---'''
        #go through each of the hot tables and move all rows where game_id is in the list of game ids needed to be moved
        for table_name in hot_tables:

            #set up the column names and list of ids that need to be moved
            col_name = 'id' if table_name == 'game' else 'game'
            ids = ','.join([str(data_id[0]) for data_id in id_list])

            #SQL commands to insert existing data into the archive table and delete it from the hot one
            copy_cmd = f"INSERT IGNORE INTO {table_name}_archive SELECT * FROM {table_name} WHERE {col_name} IN ({ids})"
            delete_query = f"DELETE FROM {table_name} WHERE {col_name} IN ({ids})"
            self._sql_cursor.execute(copy_cmd)
            '''
            There is possibility where if code gets stopped before below line is completed then DB is left in a bad state and primary keys
            will be violated in the next pass. 
            '''
            self._sql_cursor.execute(delete_query)

            rownum = self.read_query("SELECT ROW_COUNT()")
            self._log.info(f"0: gmsmvd={rownum[0][0]}")
        
        #lock in above changes made
        self._sql_conn.commit()
        return

    #Creates a backup of the full mysql db with mysqldump and zips it up for backup purposes
    @log_perf
    def create_sql_backup(self, subp = False):
        #Stores backup of mysql database, zips it up and stores either in log folder or an archive location if that is provided by the secrets file

        #going to put the full logical dump in the logs folder so that it is fast, then will zip it up and send to the archive, which may be on lower media
        fn = f"{self._db_name}_dump_{datetime.now().strftime(self._dt_frmt)}.zip"
        zip_path = os.path.join(self._log_path, fn)
        archive_zip_path = os.path.join(self._archive_path, fn)

        #linux commands to dump and zip compress the backup with gzip
        dump_cmd = f"mysqldump -u {self._config['un']} --password={self._config['pw']} {self._db_name} | gzip -9 > {zip_path}"
        cp_to_arch = f"cp {zip_path} {archive_zip_path}"
        
        try:
            #Execute command above
            subprocess.run(dump_cmd, shell=True, text=True, stdout = subprocess.DEVNULL, stderr=subprocess.STDOUT)

        except subprocess.CalledProcessError as e:
            # Handle errors if the curl command returns a non-zero exit code
            print(f"command failed with error code {e.returncode}")
            print(f"Stderr: {e.stderr}")
            raise debug_exc (subprocess.CalledProcessError, "1", {"sh_cmd":dump_cmd,"ercode":e.returncode,"ermsg":e.stderr}, "PPDB")
        
        try:
            #Execute command above
            subprocess.run(cp_to_arch, shell=True, text=True, stdout = subprocess.DEVNULL, stderr=subprocess.STDOUT)

        except subprocess.CalledProcessError as e:
            # Handle errors if the curl command returns a non-zero exit code
            print(f"command failed with error code {e.returncode}")
            print(f"Stderr: {e.stderr}")
            raise debug_exc (subprocess.CalledProcessError, "1", {"sh_cmd":cp_to_arch,"ercode":e.returncode,"ermsg":e.stderr}, "PPDB")
        
        #Call functions to clean up any old backups in the archive or log directories with their respective rules
        self._clean_archive(self._archive_path, days=2, wks=2, mnths=2)    #since backup is cold storage ok to store more. Also want to store BUs from a while ago in case problem is not found until far after bug is introduced
        self._clean_archive(self._log_path, days=1, wks=0, mnths=0)    #logs are stored in warmer storage so want to store less. Just store the most recent day and nothing more

    #Function which returns whether a datetime is valid for backing up
    def _is_backup_date(self, my_dt, bu_days, bu_mndys, bu_mnths):
            
        #get number of days away the dump is from and also pull in the file name
        diff = datetime.now() - my_dt

        #based on func args, decide if my_dt is valid for keeping a backup that day
        if diff.days < 0:
            #if time is in the future then it's safe to delete that one, something has gone wrong and log it
            return False

        elif diff.days < bu_days:
            #dont delete the file if it falls within last bu_days days
            return True

        elif diff.days < (bu_mndys*7) and my_dt.weekday() == 0:
            #dont delete the file if it falls within last bu_mndys mondays
            return True

        elif diff.days < (bu_mnths*31) and my_dt.day == 1:
            #dont delete the file if it falls on the first of the last bu_mnts months
            return True

        else:
            #if it gets here then it does not fall into a bucket worth saving
            return False

    #Function takes in path, number of months, weeks and days to keep backups for and cleans out any unnecessary backups stored at the path
    def _clean_archive(self, bu_path, days, wks, mnths ):

        #Get all file names in bu_path directory which are db dump zip files
        p = Path(bu_path)
        dmp_fs = [file_path for file_path in p.rglob(f'*{self._db_name}_dump_*.zip') if file_path.is_file()]

        #list to be filled up with all the files to remove and dict to keep track of latest backups for each day
        to_del = []
        dates = dict()
        
        #pick out the date and time of the dumps from the fn
        for (i, dt_str) in enumerate([str(fn)[-23:-4] for fn in dmp_fs]):
            
            #convert string to datetime object. If unable, log then skip it
            try:
                my_dt = datetime.strptime(dt_str, self._dt_frmt)
            except ValueError:
                self._log.warning(f"01: badfn={dmp_fs[i]} - dtstr={dt_str}")
                continue

            #If that date is valid one to be kept then check to see if that is the latest BU from that day
            if self._is_backup_date(my_dt, days, wks, mnths):
                
                day_as_str = my_dt.strftime("%y_%m_%d")

                #If no other BUs on that day, then add my_dt and file name in that spot 
                if dates.get(day_as_str) is None:
                    dates[day_as_str] = (my_dt, dmp_fs[i])

                #If existing date is same or more recent than my_dt, then can delete file corresponding to my_dt
                elif dates[day_as_str][0] >= my_dt:
                    to_del.append(dmp_fs[i])

                #If my_dt is newer than the datetime already in the dict, swap it with my_dt and cooreponding file and add the old one to the delete list
                elif dates[day_as_str][0] < my_dt:
                    to_del.append(dates[day_as_str][1])
                    dates[day_as_str] = (my_dt, dmp_fs[i])

            #If date is not one that should have it's backup saved, then just delete it
            else:
                to_del.append(dmp_fs[i])
        
        #log fns to delete and BUs
        self._log.info(f"0 del={to_del} - bus={[each[1] for each in dates.values()]}")

        #Go through each of the fns to delete and delete them
        for f_path in to_del:
            try:
                os.remove(f_path)
            except OSError:
                self._log.warning(f"02: cntdel={f_path}")
