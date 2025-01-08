class parsed_data:
    '''
    Data structure to hold all the data that was parsed from the PrizePicks API request. The structure holds both the
    data and includes infromation. Data gets its own section since it is the most importatnt arnd largest section of
    the data we get from PrizePicks. The includes are not as important but do provide useful context to what exactly
    the data all means.

    data_order - a list containing the order in which the data values will appear in the paralell lists

    data_values - a list of lista where each list contains data for each entry in the 'data' section of the prizepicks response

    included_tag_orders - a dict where each key is the name of an included type and values are the order in which the tag data is saved
    
    included_tag_values - a dict where each key is the name of an included type and values are lists of lists containing the data for each of those tags
    '''
    #In the future can data just be added into the includes section since it is really all the same format?
    data_order = None
    data_values = None
    included_tag_orders = None
    included_tag_values = None

    def __init__(self, d_order = None, d_vals = None, it_order = None, it_vals = None):
        self.data_order = d_order
        self.data_values = d_vals
        self.included_tag_orders = it_order
        self.included_tag_values = it_vals