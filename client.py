import json
import time
import socket
import urllib.request
import ssl
import uuid

import dns.resolver
import dns.inet
from pyroute2 import IPRoute


SERVERS = ['https://127.0.0.1:12345']
TOKEN = 'foobar'
FETCH = 'meineip.moritzrudert.de'
CHECKH = 'sn0{}.s.ffh.zone'
CHECK4 = '10.2.{}0.1'
CHECK6 = 'fdca:ffee:8::{}001'
RANGE = [1, 2, 4, 5, 7, 8, 9]


def check_dns(hostname, nameserver):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    try:
        result4 = resolver.query(hostname, dns.rdatatype.A)
        result6 = resolver.query(hostname, dns.rdatatype.AAAA)
    except:
        return False, False
    return result4[0], result6[0]


def check_uplink(ipv6, fetchip, checkip, fetchhost):
    netmask = '32'
    if ipv6:
        netmask = '128'
    url = 'http://{}'.format(fetchip)
    headers = {'Host': fetchhost}
    ip = IPRoute()
    # get output interface from ip route get
    oif = next(filter(lambda x: x[0] == 'RTA_OIF', ip.route('get', dst=checkip)[0]['attrs']))[1]
    ip.route('add', dst='{}/{}'.format(fetchip, netmask), gateway=checkip, oif=oif)
    request = urllib.request.Request(url, method='GET', headers=headers)
    try:
        urllib.request.urlopen(request)
    except:
        result = False
    else:
        result = True
    ip.route('del', dst='{}/{}'.format(fetchip, netmask), gateway=checkip, oif=oif)
    return result


def main():
    hosts = []
    for host in RANGE:
        flags = dict.fromkeys(['addrv4', 'addrv6', 'dnsv4', 'dnsv6', 'ulv4', 'ulv6'], False)
        hostname = CHECKH.format(host)
        fetchip4, fetchip6 = check_dns(FETCH, CHECK4.format(host))
        if fetchip4:
            flags['dnsv4'] = True
            flags['ulv4'] = check_uplink(False, fetchip4, CHECK4.format(host), FETCH)
        if fetchip6:
            flags['dnsv6'] = True
            flags['ulv6'] = check_uplink(True, fetchip6, CHECK6.format(host), FETCH)
        hosts.append({
            'host': hostname,
            'addrv4': flags['addrv4'],
            'addrv6': flags['addrv6'],
            'dnsv4': flags['dnsv4'],
            'dnsv6': flags['dnsv6'],
            'ulv4': flags['ulv4'],
            'ulv6': flags['ulv6']
        })
    name = socket.gethostname()
    uuidstr = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
    timestamp = int(time.time())
    data = {
        'timestamp': timestamp,
        'uuid': uuidstr,
        'name': name,
        'hosts': hosts
    }
    json_data = json.dumps(data).encode(encoding='utf-8')
    headers = {'content-type': 'application/json', 'X-gatemon-token': TOKEN}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = False
    for server in SERVERS:
        request = urllib.request.Request(server, data=json_data, method='POST', headers=headers)
        result = urllib.request.urlopen(request, context=ctx)
        print(result.read())


if __name__ == '__main__':
    main()
