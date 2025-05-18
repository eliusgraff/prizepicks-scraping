class parsed_data:
    '''
    Data structure to hold all the data that was parsed from the PrizePicks API request. The structure holds both the
    data and includes infromation. Data gets its own section since it is the most importatnt arnd largest section of
    the data we get from PrizePicks. The includes are not as important but do provide useful context to what exactly
    the data all means.

    data_order - a list containing the order in which the data values will appear in the paralell lists

    data_values - a list of lista where each list contains data for each entry in the 'data' section of the prizepicks response
    
    included_tag_values - a dict where each key is the name of an included type and values are dicts mapping attribute names to their values
    '''
    #In the future can data just be added into the includes section since it is really all the same format?
    data_order = list()
    data_values = list()
    included_tag_values = dict()

    def __init__(self, d_order = None, d_vals = None, it_vals = None):
        self.data_order = d_order
        self.data_values = d_vals
        self.included_tag_values = it_vals

class player_stats:
    '''
    Class to hold all the data that is parsed from the prizepick databse for a players perfromqance in a given game
    This is important to calaculate if they covered their spread or not.

    name - the name of the player

    id - the player_id assigned in the games request response - this is not the same as the player_id assigned in the
    projecttions request. I'm not sure that there is a clear way to map them, so will have to use context. I'm saving
    this just in case it becomes useful in the futures

    team - provides context for which player the stats are for

    position - this is going to be key context to making sure the correct player is attached to the correct stats. In
    the case where two players with the exact same name playe the same position, on the same team, then this will not be helpful

    dnp - did not play. This is a bool that tells us if the player played or not. PrizePicks uses this to determin if a bet needs
    to be refunded or not.
    '''
    name = None
    id = None
    team = None
    position = None
    dnp = None
    stats = None

    def __init__(self, player_name, player_id, player_team, player_postion, player_dnp, player_stats):
        self.name = player_name
        self.id = player_id
        self.team = player_team
        self.position = player_postion
        self.dnp = player_dnp
        self.stats = player_stats
