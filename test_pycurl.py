import pycurl
import certifi
from io import BytesIO
import json

buf = BytesIO()

c = pycurl.Curl()
c.setopt(c.URL, 'https://api.prizepicks.com/projections')
c.setopt(c.WRITEDATA, buf)
c.setopt(c.CAINFO, certifi.where())
c.setopt(c.ENCODING, 'gzip, deflate, br, zstd')  # Accept-Encoding / --compressed

c.setopt(c.HTTPHEADER, [
    'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language: en-US,en;q=0.5',
    'Connection: keep-alive',
    'Host: api.prizepicks.com',
    'Priority: u=0, i',
    'Sec-Fetch-Dest: document',
    'Sec-Fetch-Mode: navigate',
    'Sec-Fetch-Site: none',
    'Sec-Fetch-User: ?1',
    'TE: trailers',
    'Upgrade-Insecure-Requests: 1',
    'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
])

c.perform()
resp_code = c.getinfo(c.RESPONSE_CODE)
c.close()

print(f"Response code: {resp_code}")

body = buf.getvalue().decode('utf-8')
try:
    data = json.loads(body)
    print(json.dumps(data, indent=2))
except json.JSONDecodeError:
    print(body)
