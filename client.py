import json
import urllib.request
import ssl


def main():
    data = {
        'timestamp': 1504116111,
        'uuid': '73a1422d-f270-543b-8a60-6e3f0a56b019',
        'name': 'foo',
        'hosts': [{
            'host': 'ersterhost',
            'addrv4': 1,
            'addrv6': 0,
            'dnsv4': 1,
            'dnsv6': 0,
            'ulv4': 1,
            'ulv6': 0
        }]
    }
    json_data = json.dumps(data).encode(encoding='utf-8')
    headers = {'content-type': 'application/json'}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = False
    req = urllib.request.Request('https://127.0.0.1:12345', data=json_data, method='POST', headers=headers)
    res = urllib.request.urlopen(req, context=ctx)
    print(res.read())


if __name__ == '__main__':
    main()
