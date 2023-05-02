from loguru import logger


class Registry:
    def __init__(self):
        self._map = {}

    def register(self, keys, value):
        if isinstance(keys, str):
            keys = [keys]
        for key in keys:
            if key in self._map:
                logger.warning(
                    f'Overriding previously registered "{key}" value "{value}"'
                )
            self._map[key] = value

    def get(self, key):
        if key in self._map:
            return self._map[key]
        return None

    def get_all(self):
        return self._map.keys()
