keys = {
    'if-statement': '5-Paris',
    'comparison': '10-New York',
    'match': '8-Sydney',
    'boolean': '7-Barcelona',
    'list': '2-London',
    'slice': '10-Rome',
    'iterable': '3-San Francisco',
    'language-design': '3-Bangkok',
    'default-parameters': '2-Cape Town',
    'numpy': '1-Istanbul',
    'validation': '5-Melbourne',
    'loops': '2-Hong Kong',
    'user-input': '7-Kathmandu',
    'copy': '4-Prague',
    'clone': '3-Vancouver',
    'nested-list': '5-Buenos Aires',
    'mutable': '4-Rio De Janeiro',
    'variable-variables': '12-Berlin',
    'pandas': '10-Jerusalem',
    'iteration': '3-Montreal',
    'multidimensional-array': '3-Edinburgh',
    'flatten': '3-Venice',
    'split': '2-Hanoi',
    'chunks': '2-Amsterdam',
}


def get_tech_words(techkeys):
    _l = set(techkeys) & set(keys)
    if len(_l) == 0:
        return {'no tech keys'}
    return _l


def get_cities_from_techwords(words):
    cities_list = []
    for i in words:
        if i in keys:
            val = keys[i].split('-')
            cities_list.append(val[1])
    return set(cities_list)


def get_points_from_city(cities):
    points_list = []
    for value in keys.values():
        for city in cities:
            if city in value:
                val = value.split('-')
                points_list.append(int(val[0]))
    return sum(points_list)


'''def get_point_city_from_learned(techkeys):
    points_earned = []
    cities_list = []
    _techkeys = list(set(techkeys) & set(keys))
    print(_techkeys)
    if len(_techkeys) == 0:
        return [], 0, 'Unknown City'
    for content in _techkeys:
        if content in keys:
            val = keys[content].split('-')
            points_earned.append(int(val[0]))
            cities_list.append(val[1])
    print(points_earned)
    return _techkeys, sum(points_earned), cities_list'''
