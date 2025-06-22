from utils.log import log
from server.server import start_server
from database.database import connect_db
from utils.config import config

if __name__ == '__main__':
    connect_db()
    log.info(f'{config["project_name"]} {config["env"]} started.')
    start_server()
