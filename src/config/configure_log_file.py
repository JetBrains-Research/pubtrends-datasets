import logging
import os

def configure_log_file():
    LOG_PATHS = ['/logs', os.path.expanduser('~/.pubtrends-datasets/logs')]
    for p in LOG_PATHS:
        if os.path.isdir(p):
            logfile = os.path.join(p, 'app.log')
            break
    else:
        raise RuntimeError('Failed to configure main log file')

    logging.basicConfig(filename=logfile,
                        filemode='a',
                        format='[%(asctime)s,%(msecs)03d: %(levelname)s/%(name)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
