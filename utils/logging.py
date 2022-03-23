import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True, format='%(levelname)s:%(name)s: %(message)s')

class FogifyLogger():

    def __new__(cls, name):
        logger = logging.getLogger(f'Fogify:{name}')
        return logger

