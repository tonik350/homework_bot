import logging


def set_logging():
    logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [%(levelname)s] - %(message)s',
            handlers=[logging.FileHandler(
                'main.log',
                mode='w',
                encoding='UTF-8')]
        )
