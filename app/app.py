from utils.log import log
from server.server import start_server
from database.database import connect_db

if __name__ == '__main__':
    connect_db()
    log.info('knowledge started.')
    start_server()
