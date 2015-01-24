#!/usr/bin/env python
#coding=utf-8

import os
import sys
import time
import json
import signal
import pydablooms
import ConfigParser
#import logging

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
from mylogger import Logger

define("http_port", default=9898, help="run on the given port", type=int)
define("config", default='config.ini', help="bloomfilter config file", type=str)

define("logname", default='monitor', help="log module name", type=str)
define("logfile", default='monitor.log', help="log file", type=str)
define("logdebug", default=True, help="debug mode", type=bool)
define("loglevel", default='DEBUG', help="log level", type=str)

class Application(tornado.web.Application):
    def __init__(self, config_file, logger):
        self.logger = logger
        self.config_file = config_file
        self.bloomfilters = {}
        self._load_config_()

        handlers = [
            (r"/bloomfilter", BloomFilterHandler),
            (r"/manager", BloomFilterManagerHandler),
        ]
        settings = dict(
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        #tornado.ioloop.PeriodicCallback(self.timer, 10000).start()

    def _load_config_(self):
        if not self.config_file:
            return 
        self.conf = ConfigParser.ConfigParser()
        self.conf.read(self.config_file)
        if self.conf.has_section('bloomfilters'):
            for bfname, optvalue in self.conf.items('bloomfilters'):
                params = optvalue.split(',')
                if len(params) != 4:
                    self.logger.error('invalid bloomfilters %s %s' % (bfname, optvalue))
                    sys.exit(1)
                (bfname, capacity, error_rate, filename) = params
                self._add_bloomfilter_(bfname, capacity, error_rate, filename)

    def _add_bloomfilter_(self, bfname, capacity, error_rate, filename, isnew=False):
        capacity = int(capacity)
        error_rate = float(error_rate)
        if bfname in self.bloomfilters:
            self.logger.warn('add bloomfilter faild: %s exists' % bfname)
            return False

        if os.path.isfile(filename):
            bf = pydablooms.load_dabloom(capacity=capacity, error_rate=error_rate, filepath=filename)
            self.bloomfilters[bfname] = bf
        else:
            bf = pydablooms.Dablooms(capacity=capacity, error_rate=error_rate, filepath=filename)
            self.bloomfilters[bfname] = bf
        if isnew:
            if not self.conf.has_section('bloomfilters'):
                self.conf.add_section('bloomfilters')
            self.conf.set('bloomfilters', bfname, '%s,%s,%s,%s' % (bfname, capacity, error_rate, filename))
            if self.config_file:
                self.config_file = 'config.ini'
            self.conf.write(open(self.config_file, 'w'))
            self.logger.info('add bloomfilter %s %s %s %s' % (bfname, capacity, error_rate, filename))
        return True

    def _del_bloomfilter_(self, bfname):
        bf = self.bloomfilters[bfname]
        #delete bf
        self.bloomfilters.pop(bfname)
        if not self.conf.has_section('bloomfilters'):
            self.conf.add_section('bloomfilters')
        self.conf.remove_option('bloomfilters', bfname)
        if self.config_file:
            self.config_file = 'config.ini'
        self.conf.write(open(self.config_file, 'w'))
        self.logger.info('del bloomfilter %s' % (bfname))

    def timer(self):
        #tornado.ioloop.IOLoop.instance().add_timeout(time.time()+10, self.timer)
        self.logger.info('aaaaaaaaBBBa')

    def onsignal(self, sig, frame):
        self.logger.info('stopped')
        tornado.ioloop.IOLoop.instance().stop()

class BloomFilterHandler(tornado.web.RequestHandler):
    @property
    def logger(self):
        return self.application.logger
    @property
    def bloomfilters(self):
        return self.application.bloomfilters

    def bloomfilter(self, bfname):
        return self.bloomfilters.get(bfname, None)

    def _bf_add(self, bf, keys):
        for key in keys:
            bf.add(key)

    def _bf_del(self, bf, keys):
        for key in keys:
            bf.delete(key)

    def _bf_check(self, bf, keys):
        exists = []
        nonexists = []
        if isinstance(keys, str):
            r = bf.check(key)
            if r:
                return ([key], [])
            else:
                return ([], [key])
        if hasattr(keys, '__iter__'):
            for key in keys:
                r = bf.check(key)
                if r:
                    exists.append(key)
                else:
                    nonexists.append(key)
            return (exists, nonexists)
        else:
            return (None, None)

    def _bf_check_and_add(self, bf, keys):
        exists = []
        nonexists = []
        if isinstance(keys, str):
            r = bf.check(key)
            if r:
                return ([key], [])
            else:
                bf.add(key)
                return ([], [key])
        if hasattr(keys, '__iter__'):
            for key in keys:
                r = bf.check(key)
                if r:
                    exists.append(key)
                else:
                    bf.add(key)
                    nonexists.append(key)
            return (exists, nonexists)
        else:
            self.logger.error('invaid keys: %s' % keys)
            return ([], [])

    def get(self):
        errcode = 0
        errmsg = 'success'
        try:
            bfname = self.get_argument("bf", None)
            action = self.get_argument("action", None)
            key = self.get_argument("key", None)
            if (not bfname) or (not action) or (not key) :
                raise ValueError('bf action key are needed')
            bf = self.bloomfilter(bfname)
            if not bf:
                raise ValueError("bloomfilter for '%s' not exist" % bfname)
            support_actions = ['add', 'del', 'check', 'contain', 'contains', 'checkadd', 'check_and_add']
            if action not in support_actions:
                raise ValueError('action for %s not support' % bfname)
            keys = key.split(',')
            #self.actions[action](bf, keys)
            if action == 'add':
                self._bf_add(bf, keys)
            elif action == 'del':
                self._bf_del(bf, keys)
            elif action == 'check' or action == 'contain' or action == 'contains':
                exits, nonexists = self._bf_check(bf, keys)
                ret_msg = {'errno': errcode, "msg": errmsg, 'exits': exits, 'nonexists': nonexists}
                self.write(ret_msg)
                self.logger.info('check %s %s' % (bfname, ret_msg))
                return
            elif action == 'checkadd' or action == 'check_and_add':
                exits, nonexists = self._bf_check_and_add(bf, keys)
                ret_msg = {'errno': errcode, "msg": errmsg, 'exits': exits, 'nonexists': nonexists}
                self.write(ret_msg)
                self.logger.info('check %s %s ret=%s' % (bfname, key, ret_msg))
                return
        except Exception, e:
            self.logger.exception(e)
            errcode = -1
            errmsg = e.message
        #ret_msg = {'errno': errcode, 'msg': errmsg, 'usage': '/filter?bf=xxx&action=add|del|check|checkadd&key=key1,key2'}
        ret_msg = {'errno': errcode, 'msg': errmsg}
        self.write(ret_msg)
        return

    def post(self):
        self.get()
            
class BloomFilterManagerHandler(tornado.web.RequestHandler):

    @property
    def logger(self):
        return self.application.logger

    @property
    def bloomfilters(self):
        return self.application.bloomfilters

    def bloomfilter(self, bfname):
        return self.bloomfilters.get(bfname, None)

    def _add_bloomfilter_(self, bfname, capacity, error_rate, filepath):
        return self.application._add_bloomfilter_(bfname, capacity, error_rate, filepath, isnew=True)

    def _del_bloomfilter_(self, bfname):
        return self.application._del_bloomfilter_(bfname)
        
    def get(self):
        errcode = 0
        errmsg = 'success'
        try:
            bfname = self.get_argument("bf", None)
            action = self.get_argument("action", None)
            if (not bfname) or (not action):
                raise ValueError('bf action are needed')
            support_actions = ['add', 'del']
            if action not in support_actions:
                raise ValueError('action for %s not support' % bfname)
            import pdb
            pdb.set_trace()
            if action == 'add':
                bf = self.bloomfilter(bfname)
                if bf:
                    raise ValueError("bloomfilter for '%s' has exist" % bfname)
                capacity = self.get_argument("capacity", None)
                error_rate = self.get_argument("error_rate", None)
                filename = '%s.bloom.bin' % bfname
                self._add_bloomfilter_(bfname, capacity, error_rate, filename)
            elif action == 'del':
                bf = self.bloomfilter(bfname)
                if not bf:
                    raise ValueError("bloomfilter for '%s' not exist" % bfname)
                self._del_bloomfilter_(bfname)
        except Exception, e:
            self.logger.exception(e)
            errcode = -1
            errmsg = e.message
        ret_msg = {'errno': errcode, 'msg': errmsg}
        self.write(ret_msg)
        return

    def post(self):
        self.get()

def main():
    tornado.options.parse_command_line()

    logger = Logger.getLogger(options.logname, options.logfile, level=options.loglevel, debug=options.logdebug)

    application = Application(options.config, logger)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.http_port)
    logger.info('listen %s' % options.http_port)

    #这里是绑定信号处理函数，将SIGTERM绑定在函数onsignal_term上面    
    signal.signal(signal.SIGTERM, application.onsignal)  
    signal.signal(signal.SIGINT, application.onsignal)  

    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
