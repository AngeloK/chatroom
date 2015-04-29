
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


class MainHandler(RequestHandler):

    def get(self):
        return self.render("index.html")

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
        self.cache.extend([ message ])
        if len(self.cache)>self.cache_size:
            self.cache = self.cache[-self.cache_size:]

    def cancel_wait(self,future):
        try:
            self.waiters.remove(future)
            future.set_result([])
        except KeyError,e:
            logging.error("Key error:%s",e)


    def wait_for_messages(self,cursor=None):
        
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
                result_future.set_result(self.cache[-new_count:])
                return 

global_message_buffer = MessageBuffer()
        
class MessageNewHandler(RequestHandler):

    def post(self):
        id_ = uuid.uuid4()
        body = self.get_argument("body")
        message = dict(cursor=id_,body=body) 
        global_message_buffer.new_message(message)

class MessageUpdatesHandler(RequestHandler):
    @gen.coroutine
    def post(self):
        cursor = get_argument("cursor",None)
        self.future = global_message_buffer.wait_for_messages(cursor=cursor)
        messages = yield self.future
        if self.request.connection.start.closed():
            return
        self.write(dict(messages=messages))


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
            xsrf_cookies = True,
            debug = options.debug, 
        )
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()



