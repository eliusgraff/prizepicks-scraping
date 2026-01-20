
#Simple circular buffer class
class circular_buffer:

    _buffer = []
    _head = 0
    _my_len = 0

    #Constructor to create buffer and configure if type-checking should be done
    def __init__(self, l, fill = None):
        
        assert l > 0
        self._buffer = [fill]*l
        self._my_len = l

    #Function to add to front of buffer
    def push_back(self, item):
        #move head to next spot and put in new item
        self._adv_head()
        self._buffer[self._head] = item

    #return buffer in order
    def get_buffer(self):
        return self._buffer[self._head:]+self._buffer[:self._head]

    #Move head to next spot in the buffer
    def _adv_head(self):
        self._head += 1
        if self._head == self._my_len:
            self._head = 0

    def head(self):
        return self._buffer[self._head]
