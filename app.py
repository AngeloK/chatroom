
import logging
import uuid
import os
import MySQLdb
import subprocess
import torndb
import bcrypt

import tornado
from tornado.concurrent import Future
from tornado import gen
from tornado.web import RequestHandler
from tornado.options import define
from tornado.options import options
from tornado.options import parse_command_line

define("port",default=8000,help="run port",type=int)
define("debug",default=True,help="develop mode")
define("mysql_host",default="localhost",help="database host")
define("mysql_database",default="chatroom",help="database name")
define("mysql_user",default="root",help="database user")
define("mysql_password",default="",help="password")

#executor = concurrent.futures.ThreadPoolExecutor(2)


class Application(tornado.web.Application):

    def __init__(self):

        handlers = [
            (r"/",MainHandler),
            (r"/message/new",MessageNewHandler),
            (r"/message/update",MessageUpdatesHandler),
            (r"/new",UserHandler),
            (r"/login",UserAuthenticateHandler)
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret = "__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            ui_modules = {"Message":MessageModule},
            xsrf_cookies = True,
            debug = options.debug, 
        )

        super(Application, self).__init__(handlers,**settings)

        self.db = torndb.Connection(
            host = options.mysql_host, database = options.mysql_database,
            user = options.mysql_user, password = options.mysql_password,
        )
    
        self.create_databse_if_not_exsit()

    def create_databse_if_not_exsit(self):
        try:
            self.db.get("select COUNT(*) from messages")
        except MySQLdb.ProgrammingError:
            subprocess.check_call(['mysql',
                       '--host=' + options.mysql_host,
                       '--database=' + options.mysql_database,
                       '--user=' + options.mysql_user,
                       '--password=' + options.mysql_password],
                      stdin=open('chatroom.sql'))

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

class BaseHandler(RequestHandler):
    
    @property
    def db(self):
        return self.application.db

    #def get_current_user(self):
        #user_id = get_secure_cookie("user")
        #return None if not user_id

    def check_if_exist(self,email):
        user = self.db.get("SELECT * FROM users WHERE email=%s",email)
        if user:
            return True
        return False

    def get_password(self,email):

        return self.db.get("SELECT password FROM users where email=%s",email)



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
        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=messages))

class MessageModule(tornado.web.UIModule):

    def render(self,message):
        return self.render_string("message.html",message=message)

class UserHandler(BaseHandler):

    def get(self):
        return self.render("create_user.html") 

    def post(self):
        email = self.get_argument("email")
        if self.check_if_exist(email):
            raise tornado.web.HTTPError(400,"User existed!")
        else:
            password = bcrypt.hashpw(self.get_argument("password"),
                    bcrypt.gensalt()) 

            user_id = self.db.execute(
                "INSERT INTO users ('name','email','password')"
                "VALUES (%s,%s,%s)",
                self.get_argument("name"),self.get_argument("email"),
                password) 

            self.set_cookie("chat_user",user_id)
            self.redirect(self.get_argument("next"),"/")
            
class UserAuthenticateHandler(BaseHandler):

    def get(self):
        return self.render("login.html")

    def post(self):
        email = self.get_argument("email")

        if not self.check_if_exist(email):
            raise tornado.web.HTTPError(400,"authenticate fail")

        password = self.get_argument("password")
        hashed_password = self.get_password(email)
        
        if bcrypt.hashpw(password,hashed_password) == hashed_password:
            user_id = self.db.get("SELECT id from users where email=%s",email)
            self.set_cookie("chat_user",user_id)
            self.redirect(self.get_argument("next","/"))

def main():
    parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()



