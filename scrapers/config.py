HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8,de;q=0.7',
}

MIN_DELAY = 2
MAX_DELAY = 4
MIN_PRICE = 3000
MAX_PRICE = 50000

TOYOTA_MODELS = {
    '8FBE15': {'type': 'electric', 'capacity': '1500kg'},
    '8FBE18': {'type': 'electric', 'capacity': '1800kg'},
    '8FBE20': {'type': 'electric', 'capacity': '2000kg'},
    '8FD25': {'type': 'diesel', 'capacity': '2500kg'},
    '8FG30': {'type': 'lpg', 'capacity': '3000kg'},
    'RRE140': {'type': 'reach', 'capacity': '1400kg'},
}

MARKETS = {
    'NL': {'name': 'Netherlands', 'currency': 'EUR'},
    'BE': {'name': 'Belgium', 'currency': 'EUR'},
    'DE': {'name': 'Germany', 'currency': 'EUR'},
}
