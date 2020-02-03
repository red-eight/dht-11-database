import logging
import sys

from aiohttp import web
import toml

from humidity.routes import get_application


def setup_logging(config):
    log = logging.getLogger()
    log.setLevel(config['log']['level'])
    log.addHandler(logging.StreamHandler(sys.stdout))

    return log


def main():
    config = toml.load('config.toml')
    log = setup_logging(config)

    log.info('===Starting up====')

    app = get_application(config)

    web.run_app(app)


if __name__ == '__main__':
    main()
