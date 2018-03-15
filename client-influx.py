import json
import socket
import urllib.request

import influxdb
import dns.resolver
import dns.inet
from pyroute2 import IPRoute
from scapy.all import conf, get_if_raw_hwaddr, Ether, IP, UDP, BOOTP, DHCP, srp1


def get_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return None


def create_json(hostname, montype, supernode, value):
    measurement = 'nodemonitoring_{}'.format(montype)
    json_body = {
        "measurement": measurement,
        "tags": {
            "tester": hostname,
            "supernode": supernode,
            "domain": "default"
        },
        "fields": {
            "Bool_value": value,
            "Int_value": int(value)
        }
    }
    return json_body


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


def check_dhcp(interface, server):
    ip = IPRoute()
    client = ip.get_addr(label=interface)[0]['attrs'][0][1]
    conf.iface = interface
    hwaddr = bytes(get_if_raw_hwaddr(conf.iface))
    dhcp_discover = Ether() / \
                    IP(dst=server) / \
                    UDP(dport=67, sport=68) / \
                    BOOTP(chaddr=hwaddr) / \
                    DHCP(options=[
                        ('message-type', 'request'),
                        ('requested_addr', client),
                        'end'
                    ])
    dhcp_offer = srp1(dhcp_discover, timeout=5, verbose=False)
    if dhcp_offer is None:
        return False
    else:
        if '10.2.' in dhcp_offer.yiaddr:
            return True
        else:
            return False


def main():
    config = get_json('client.json')
    if config is None:
        print('There is no config file.')
        return False
    try:
        influx = config['influx']
        fetch = config['fetch']
        check = config['check']
        check4 = config['check4']
        check6 = config['check6']
        nodes = config['nodes']
        device = config['device']
    except KeyError:
        print('Malformed config file.')
        return False
    tester = socket.gethostname()
    influxcli = influxdb.InfluxDBClient.from_dsn(dsn=influx, timeout=30)
    points = []
    for node in nodes:
        name = check.format(node)
        print(name)
        fetchip4, fetchip6 = check_dns(fetch, check4.format(node))
        if fetchip4:
            points.append(create_json(tester, 'dnsv4', name, True))
            points.append(create_json(tester, 'ulv4', name, check_uplink(False, fetchip4, check4.format(node), fetch)))
        else:
            points.append(create_json(tester, 'dnsv4', name, False))
            points.append(create_json(tester, 'ulv4', name, False))
        if fetchip6:
            points.append(create_json(tester, 'dnsv6', name, True))
            points.append(create_json(tester, 'ulv6', name, check_uplink(True, fetchip6, check6.format(node), fetch)))
        else:
            points.append(create_json(tester, 'dnsv6', name, False))
            points.append(create_json(tester, 'ulv6', name, False))
        points.append(create_json(tester, 'dhcp', name, check_dhcp(device, check4.format(node))))
    if influxcli.write_points(points=points, protocol='json'):
        return True
    else:
        return False


if __name__ == '__main__':
    main()
