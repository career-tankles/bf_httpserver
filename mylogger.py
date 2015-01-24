#coding=utf-8

import sys
import time
import logging
from logging.handlers import TimedRotatingFileHandler

level_d = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARN,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.FATAL,
}

class Logger(object):
    @staticmethod
    def getLogger(logger_name, log_file, level='DEBUG', debug=True):
        logger_ = logging.getLogger(logger_name)
        logger_.setLevel(level_d.get(level, logging.DEBUG))
        formater = logging.Formatter('[%(asctime)s] %(name)s %(filename)s +%(lineno)d %(levelname)s %(message)s')
        handler = None
        if (not debug) and log_file:
            handler = TimedRotatingFileHandler(log_file, 'h', 1, 24*10)
        else:
            handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formater)
        logger_.addHandler(handler)
        return logger_

    @staticmethod
    def addLoggingServer(logger, server_host, server_port, server_path='/log', method='GET', level='ERROR'):
        if server_host and server_port:
            http_handler = logging.handlers.HTTPHandler(
                '%s:%s' % (server_host, server_port),
                server_path,
                #method='POST'
                method=method,
            )
            http_handler.setLevel(level_d.get(level, logging.ERROR))
            logger.addHandler(http_handler)

class Loggers(object):
    def __init__(self, log_dir='log', default_level='INFO', default_debug=False, \
                default_loggingserver_host=None, default_loggingserver_port=None, \
                default_loggingserver_path='/log', default_loggingserver_level='ERROR', \
                default_loggingserver_method='GET'):
        self.log_dir = log_dir
        self.default_level = default_level
        self.default_debug = default_debug
        self.default_loggingserver_host = default_loggingserver_host
        self.default_loggingserver_port = default_loggingserver_port
        self.default_loggingserver_path = default_loggingserver_path
        self.default_loggingserver_level = default_loggingserver_level
        self.default_loggingserver_method = default_loggingserver_method
        self.loggers = {}

    def __getitem__(self, logger_name):
        if logger_name not in self.loggers:
            logger_ = Logger.getLogger(logger_name, '%s/%s.log' % (self.log_dir, logger_name), self.default_level, self.default_debug)
            if self.default_loggingserver_host and self.default_loggingserver_port:
                Logger.addLoggingServer(logger_, self.default_loggingserver_host, self.default_loggingserver_port, self.default_loggingserver_path, self.default_loggingserver_method, self.default_loggingserver_level)
            self.loggers[logger_name] = logger_
        return self.loggers[logger_name]

    def __setitem__(self, logger_name, logger):
        self.loggers[logger_name] = logger

if __name__ == "__main__":
    default_level = 'INFO'
    default_debug = False
    default_loggingserver_host = None  # 禁用logging server
    default_loggingserver_port = 9898
    default_loggingserver_path = '/log'
    default_loggingserver_level = 'ERROR'
    default_loggingserver_method = 'GET'
    loggers = Loggers('log', default_level, default_debug, \
                      default_loggingserver_host, default_loggingserver_port,  \
                      default_loggingserver_path, default_loggingserver_level, \
                      default_loggingserver_method)
    loggers['online'].error('aaaaaaaaaaaaaaaaaaaaaaONLINEaaaaaaaaaaaaaaaaaaaaaaaaaaa')
    loggers['debug'].error('aaaaaaaaaaaaaaaaaaaaaaDEBUGaaaaaaaaaaaaaaaaaaaaaaaaaaa')

    sys.exit(1)

    logger_debug = Logger.getLogger('debug', None, 'DEBUG', True) # <==> logger = Logger.getLogger('spider') # debug
    logger_online = Logger.getLogger('online', 'online.log', 'INFO', False) # <==> logger = Logger.getLogger('spider') # debug
    #logger = logger_debug
    logger = logger_online
    Logger.addLoggingServer(logger, '127.0.0.1', 9900)

    while True:
        logger.debug('debug message')
        logger.info('info message')
        logger.warn('warn message')
        logger.error('error message')
        logger.critical('critical message')
    
        #logger.log(logging.INFO, "We have a %s", "mysterious problem", exc_info=1)
        logger.log(logging.INFO, 'We have a %s %s', "mysterious problem", 'bb')
        #try:
        #    raise ValueError('exception value Error')
        #except Exception, e:
        #    logger.exception(e)
    
        #time.sleep(2)

 
