from django.core.management.base import BaseCommand

from edflex.tasks import fetch_edflex_data

import logging
import time
from datetime import datetime


logger = logging.getLogger("edflex_xblock")
log_handler = logging.handlers.TimedRotatingFileHandler('/edx/var/log/lms/edflex_xblock_update.log',
                                                        when='D',
                                                        interval=10,
                                                        backupCount=4,
                                                        encoding='utf-8')
log_formatter = logging.Formatter(u'%(asctime)s [%(name)s] [%(filename)s:%(lineno)d] %(levelname)s  - %(message)s')
log_formatter.converter = time.gmtime
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)
logger.addHandler(log_handler)


class Command(BaseCommand):

    def handle(self, *args, **options):
        logger.info("Starting fetching the new edflex data...")
        start_time = datetime.now()

        fetch_edflex_data()

        logger.info("Finished fetching the new edflex data after {}".format(datetime.now() - start_time))