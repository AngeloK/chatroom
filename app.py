# -*- coding:utf-8 -*-

import logging
import uuid
import os
import MySQLdb
import subprocess
import torndb
import bcrypt

import tornado
import concurrent.futures
from tornado.concurrent import Future
from tornado import gen
from tornado.web import RequestHandler
from tornado.options import define
from tornado.options import options
from tornado.options import parse_command_line

define("port", default=8000, help="run port", type=int)
define("debug", default=True, help="develop mode")
define("mysql_host", default="localhost", help="database host")
define("mysql_database", default="chatroom", help="database name")
define("mysql_user", default="root", help="database user")
define("mysql_password", default="", help="password")

executor = concurrent.futures.ThreadPoolExecutor(2)


class Application(tornado.web.Application):

    def __init__(self):

        handlers = [
            (r"/", MainHandler),
            (r"/message/new", MessageNewHandler),
            (r"/message/update", MessageUpdatesHandler),
            (r"/new", UserCreateHandler),
            (r"/login", UserAuthenticateHandler),
            (r"/logout", UserLogoutHandler)
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            ui_modules={"Message": MessageModule},
            login_url="/login",
            xsrf_cookies=True,
            debug=options.debug
        )

        super(Application, self).__init__(handlers, **settings)

        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password,
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


class BaseUserHandler(RequestHandler):

    @property
    def db(self):
        return self.application.db

    def check_if_exist(self, email):
        user = self.db.get("SELECT * FROM users WHERE email= %s", email)
        if user:
            return True
        return False

    def get_password(self, email):
        row = self.db.get("SELECT password FROM users where email= %s", email)
        if row:
            return row["password"]
        else:
            return

    def get_current_user(self):
        user_name = self.get_secure_cookie("chat_user")
        if not user_name:
            return None
        return self.db.get("SELECT * FROM users WHERE name= %s", user_name)


class MessageBuffer(object):

    def __init__(self):
        self.waiters = set()
        self.cache = []
        self.cache_size = 200

    def new_message(self, message):
        logging.info("new message create for %d listeners" % len(self.waiters))

        for future in self.waiters:
            future.set_result(message)

        self.waiters = set()
        self.cache.extend(message)
        logging.info("### message in cache: %s", self.cache)
        if len(self.cache) > self.cache_size:
            self.cache = self.cache[-self.cache_size:]

    def cancel_wait(self, future):
        try:
            self.waiters.remove(future)
            future.set_result([])
        except KeyError as e:
            logging.error("Key error: %s", e)

    def wait_for_messages(self, cursor=None):
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


class MainHandler(BaseUserHandler):

    @tornado.web.authenticated
    def get(self):
        return self.render("index.html", messages=global_message_buffer.cache)


class MessageNewHandler(RequestHandler):

    def post(self):
        id_ = str(uuid.uuid4())
        body = self.get_argument("body")
        current_user = self.get_secure_cookie("chat_user")
        logging.info("current user: %s" % current_user)
        message = dict(id=id_, body=body, user_name=current_user)
        self.write(message)
        global_message_buffer.new_message([message])
        logging.info("new message created,message: %s" % message)


class MessageUpdatesHandler(RequestHandler):

    @gen.coroutine
    def post(self):
        cursor = self.get_argument("cursor", None)
        self.future = global_message_buffer.wait_for_messages(cursor=cursor)
        logging.info("+++ self.future: %s" % self.future)
        messages = yield self.future
        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=messages))


class MessageModule(tornado.web.UIModule):

    def render(self, message):
        return self.render_string("message.html", message=message)


class UserCreateHandler(BaseUserHandler):

    def get(self):
        if self.get_current_user():
            self.redirect("/")
            return
        return self.render("create_user.html")

    @gen.coroutine
    def post(self):
        email = self.get_argument("email")
        print(email)
        if self.check_if_exist(email):
            raise tornado.web.HTTPError(400, "User existed!")
        else:
            password = yield executor.submit(
                bcrypt.hashpw, tornado.escape.utf8(
                    self.get_argument("password")), bcrypt.gensalt())
            user_id = self.db.execute(
                "INSERT INTO users (`name`,`email`,`password`) "
                "VALUES (%s,%s,%s)",
                self.get_argument("name"), self.get_argument("email"),
                password)
            self.set_secure_cookie("chat_user", self.get_argument("name"))


class UserAuthenticateHandler(BaseUserHandler):

    def get(self):
        user = self.get_current_user()
        if user:
            self.redirect("/")
        self.render("login.html")

    @gen.coroutine
    def post(self):
        email = self.get_argument("email")

        if not self.check_if_exist(email):
            raise tornado.web.HTTPError(
                400,
                "authenticate fail,no user founded")

        user = self.db.get("SELECT * FROM users WHERE email=%s",
                           email)

        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            tornado.escape.utf8(user.password))

        if hashed_password == user.password:
            self.set_secure_cookie("chat_user", user.name)
        else:
            raise tornado.web.HTTPError(400, "wrong password")


class UserLogoutHandler(BaseUserHandler):

    def get(self):
        if self.get_secure_cookie("chat_user"):
            self.clear_cookie("chat_user")
        else:
            pass
        self.redirect("/")


def main():
    parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
