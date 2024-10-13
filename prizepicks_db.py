import mysql.connector
import helper

#Long term, this should not need to be root user
def root_login():
    '''
    This function is used to retrive the username, host name, and password to gain access to the local
    mySQL database. requires that the user have a file called 'secrets.txt' where 3 of the lines in it are:
    mysql_un=username
    mysql_pw=password
    mysql_hn=hostname
    
    So, to access this, that file must be setup beforehand and then this function will work properly as it
    is simply reading those 3 items from the file. It muse have *accurate* user info of the 3
    fields above to get into the SQL DB
    '''
    my_dict = helper.get_secret("mysql")
    '''---Checking to make sure all the necessary parts were read from file---'''
    not_found_list = []
    if my_dict.get('un') is None: not_found_list.append('un')
    if my_dict.get('pw') is None: not_found_list.append('pw')
    if my_dict.get('hn') is None: not_found_list.append('hn')
    if len(not_found_list) > 0:
        print(f"WARNING: Missing values in dict:{not_found_list}")
        return None

    return my_dict

def create_db_connection(db_name="prizepicks", host_name= None, user_name = None, user_password = None):
    '''
    Function to create a connection to the local mySQL database. Credentials can be passed in or they default to None and if host_name is left as None
    then the root_login() function will get the root login data form a file somewhere on the computer
    '''
    if host_name is None:
        creds = root_login()
        host_name = creds['hn']
        user_name = creds['un']
        user_password = creds['pw']

    connection = mysql.connector.connect(
        host=host_name,
        user=user_name,
        passwd=user_password,
        database=db_name
    )

    print("MySQL Database connection successful")
    return connection

def list_to_db( table, headers, data, cursor):
    '''
    Function which will send passed in descriptors and data to the local prizepicks mySQL database
    Argumetns are:
        table - name of the table the data will be inserted into
            ex: "new_player" or "lfg_ignored_leagues"
        headers - a list of names of the columns of the target table in order for how they apprear in the data
            ex: ["id", "name", "position", "image_url", "display_name", "combo", "league_id", "team_id"] or ["id", "league_num"]
        data - a list of lists where each sub-list is the list of data that is going into the database. The data point at each index is
            described by that same index of 'headers' list
            ex: [
                ['172250', 'Jude Bellingham', 'Midfielder', 'https://static.prizepicks.com/images/players/soccer/e83ula4wockmc2xid7185kcq2.webp', 'Jude Bellingham', False, 82, '3372'],
                ['197873', 'Jyllissa Harris', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Houston_Dash.webp', 'Jyllissa Harris', False, 82, '4156'],
                ['171076', 'JÃ¸rgen Strand Larsen', 'Attacker', 'https://static.prizepicks.com/images/manual/JÃ¸rgen Strand Larsen.png', 'JÃ¸rgen Strand Larsen', False, 82, '3356'],
                ['215896', 'Courtney Petersen', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Racing_Louisville.webp', 'Courtney Petersen', False, 82, '4160']
                ]
                or
                [
                ['718', 82]
                ]
    '''
    '''---Creating the query strings based on descriptors---'''
    col_list =  "("
    query_toks = "("
    for col in headers: 
        col_list += f"{col},"
        query_toks += "%%s,"
    col_list[-1] = ")"
    query_toks[-1] = ")"
    command = f"INSERT INTO {table} {col_list} VALUES {query_toks}"
    values = data
    cursor.executemany(command, values)


def send_to_sql(data_cols, data_values, includes_cols, include_values):
    '''---Creating mysql connecrtion and cursor objects so we can set up the transfer---'''
    conn = create_db_connection()
    cursor = conn.cursor()
    
    '''---Sending the values for the 'data' table to mySQL---'''
    list_to_db('data', data_cols, data_values, cursor)

    '''---Going through all the includes and adding those now---'''
    for name, cols in includes_cols.items():
        list_to_db(name, cols, include_values[name])

    '''---Saving changes to the databse and closing the connection---'''
    #I should look into what it best practive and when to commit the sql executions I think I like doing it at the end so that if something goes wrong then just nothing is added and it's no problem
    #conn.commit()
    conn.close()