from django.core.management.base import BaseCommand

from edflex.tasks import update_resources

import logging
import time
from datetime import datetime

logger = logging.getLogger("edflex_xblock")
log_handler = logging.handlers.TimedRotatingFileHandler('/edx/var/log/lms/edflex_xblock.log',
                                                        when='D',
                                                        backupCount=1,
                                                        encoding='utf-8')
log_formatter = logging.Formatter(u'%(asctime)s %(levelname)s  - %(message)s')
log_formatter.converter = time.gmtime
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)
logger.addHandler(log_handler)

log_handler_error = logging.handlers.TimedRotatingFileHandler('/edx/var/log/lms/edflex_xblock_error.log',
                                                        when='D',
                                                        backupCount=1,
                                                        encoding='utf-8')
log_handler_error.setFormatter(log_formatter)
log_handler_error.setLevel(logging.ERROR)
logger.addHandler(log_handler_error)

class Command(BaseCommand):

    def handle(self, *args, **options):
        logger.info("Starting updating the resource data...")
        start_time = datetime.now()

        update_resources()

        logger.info("Finished updating the resource data after {}".format(datetime.now() - start_time))
