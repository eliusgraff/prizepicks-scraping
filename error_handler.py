class error_handler:

    cmds = None
    log_path = None
    consec_errors = None

    def __init__(self, cmd_list, log_path):
        self.cmds = cmd_list
        self.log_path = log_path
