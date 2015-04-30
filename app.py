
import logging
import uuid
import os

import tornado
from tornado.concurrent import Future
from tornado import gen
from tornado.web import RequestHandler
from tornado.options import define,options,parse_command_line

define("port",default=8000,help="run port",type=int)
define("debug",default=True,help="develop mode")



class MessageBuffer(object):

    def __init__(self):
        self.waiters = set()
        self.cache = []
        self.cache_size = 200

    def new_message(self,message):
        logging.info("new message create for %d listeners" %len(self.waiters))

        for future in self.waiters:
            future.set_result(message)

        self.waiters = set()
        self.cache.extend(message)
        logging.info("### message in cache: %s",self.cache)
        if len(self.cache)>self.cache_size:
            self.cache = self.cache[-self.cache_size:]

    def cancel_wait(self,future):
        try:
            self.waiters.remove(future)
            future.set_result([])
        except KeyError,e:
            logging.error("Key error:%s",e)


    def wait_for_messages(self,cursor=None):
        '''
        cursor used for mark the id of the newest message.
        '''
        result_future = Future()
        if not cursor:
            logging.info("new listner joined")
            self.waiters.add(result_future)
            return result_future
        else:
            new_count = 0
            for msg in reversed(self.cache):
                if msg['id'] == cursor:
                    break
                new_count = new_count+1
            if new_count:
                result_future.set_result(self.cache[-new_count:])
            self.waiters.add(result_future)
            return result_future 

global_message_buffer = MessageBuffer()
        
class MainHandler(RequestHandler):

    def get(self):
        return self.render("index.html",messages=global_message_buffer.cache)

class MessageNewHandler(RequestHandler):

    def post(self):
        id_ = str(uuid.uuid4())
        body = self.get_argument("body")
        message = dict(id=id_,body=body) 
        self.write(message)
        global_message_buffer.new_message([message])
        logging.info("new message created,message:%s" %message)

class MessageUpdatesHandler(RequestHandler):
    @gen.coroutine
    def post(self):
        cursor = self.get_argument("cursor",None)
        self.future = global_message_buffer.wait_for_messages(cursor=cursor)
        logging.info("+++ self.future: %s"%self.future)
        messages = yield self.future
        logging.info("+++++ Yield Messages: %s" %messages)
        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=messages))

class MessageModule(tornado.web.UIModule):

    def render(self,message):
        return self.render_string("message.html",message=message)


def main():
    parse_command_line()
    app = tornado.web.Application(
            [
                (r"/",MainHandler),
                (r"/message/new",MessageNewHandler),
                (r"/message/update",MessageUpdatesHandler)
            ],
            cookie_secret = "__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path = os.path.join(os.path.dirname(__file__),"templates"),
            static_path = os.path.join(os.path.dirname(__file__),"static"),
            ui_modules = {"Message":MessageModule},
            xsrf_cookies = True,
            debug = options.debug, 
        )
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()



