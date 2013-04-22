#! /usr/bin/python
#coding=utf-8

import psycopg2
from txpostgres import txpostgres
from zope.interface.interfaces import Interface
from zope.interface.declarations import implements
from twisted.internet import reactor, defer

# ==========|SQL-КОМАНДЫ|==========

SQL_SELECT_CONTEST = "SELECT \
CONTEST_ID \
, TITLE \
, START_DATE \
, END_DATE \
, HQ_PLACE \
, HQ_COUNTRY \
, HQ_LAT \
, HQ_LON \
FROM CONTEST \
WHERE CONTEST_ID = %s\
"

SQL_INSERT_CONTEST = "INSERT INTO CONTEST( \
TITLE \
, START_DATE \
, END_DATE \
, HQ_PLACE \
, HQ_COUNTRY \
, HQ_LAT \
, HQ_LON \
) VALUES (%s, %s, %s, %s, %s, %s, %s) \
RETURNING CONTEST_ID\
"

SQL_UPDATE_CONTEST = "UPDATE CONTEST SET \
TITLE = %s \
, START_DATE = %s \
, END_DATE = %s \
, HQ_PLACE = %s \
, HQ_COUNTRY = %s \
, HQ_LAT = %s \
, HQ_LON = %s \
WHERE CONTEST_ID = %s\
"

# ==========|НУЖНО ДЛЯ РАБОТЫ ЭТОГО ТЕСТА|==========

connectionParams = {
    "server":"localhost",
    "dbname":"airtribune",
    "user":"airtribune",
    "password":"airtribune",
    "schema":"airtribune_test"
}

class ContestFactory(object):
    def __init__(self):
        pass

    def create_contest(self, id, title, start_time, end_time,
                       contest_place, contest_country, hq_coords):
        print "create contest %r, %r, %r, %r, %r, %r, %r" % (id, title, start_time, end_time, contest_place, contest_country, hq_coords)
        return Contest(id, title, start_time, end_time, contest_place, contest_country, hq_coords)

class IContestRepository(Interface):
    def get_by_id(id): # @NoSelf
        '''
        '''
    def save(person): # @NoSelf
        '''
        '''

class NoAggregate(Exception):
    pass    

class Contest(object):
    def __init__(self, contest_id, title, start_time, end_time, contest_place, contest_country, hq_coords):
        self.id = contest_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.contest_place = contest_place
        self.contest_country = contest_country
        self.hq_coords = hq_coords

# ==========|ПУЛ СОЕДИНЕНИЙ|==========

# Менеджер соединений. Создает соединения и хранит ссылки на них.

class ConnectionManager(object):
    def __init__(self):
        self.pool = txpostgres.ConnectionPool(None, 
            host="localhost", database="airtribune",
            user="airtribune", password="airtribune")

    def pool(self):
        return self.pool

    # Открывает синхронное соединение (оставлено для совместимости)
    def open_connection(self):
        global connectionParams
        server_name = connectionParams["server"]
        db_name = connectionParams["dbname"]
        user_name = connectionParams["user"]
        user_pass = connectionParams["password"]
        schema_name = connectionParams["schema"]

        connection = psycopg2.connect(
            host = server_name, 
            database = db_name, 
            user = user_name, 
            password = user_pass)
        return connection

    # Открывает асинхронное соединение
    # ВНИМАНИЕ!
    # 1. ИМ НЕЛЬЗЯ ВОСПОЛЬЗОВАТЬСЯ ДО МОМЕНТА ГОТОВНОСТИ
    # 2. НАДО САМОМУ СЛЕДИТЬ ЗА ТЕМ, ВЫПОЛНЕНА КОМАНДА ИЛИ НЕТ
    def open_async_connection(self):
        # Проверяем, есть ли у нас свободные, но ранее открытые соединения
        if len(self.free_connections) == 0:
            # Если нет - открываем новое. Данные для установления соединения сейчас лежат в connectionParams
            global connectionParams
            server_name = connectionParams["server"]
            db_name = connectionParams["dbname"]
            user_name = connectionParams["user"]
            user_pass = connectionParams["password"]
            connection = psycopg2.connect(
                host = server_name, 
                database = db_name, 
                user = user_name, 
                password = user_pass,
                async = True)
            # Увеличиваем счетчик открытых соединений на 1. 
            # Это уникальный идентификатор соединения, нужный для корректного освобождения, 
            # поэтому единственное, где мы его меняем - это прибавляем 1 при открытии нового соединения.
            # Мы никогда не уменьшаем его.
            self.connections_counter += 1
            connection_id = self.connections_counter
            # Созраняем открытое соединение в used_connections и возвращаем пару (ID, соединение)
            self.used_connections[connection_id] = connection
            return (connection_id, connection)
        else:
            # Если есть свободное - достаем его из free_connections переносим в used_connections и возвращаем пару
            data_pair = self.free_connections.popitem()
            self.used_connections[data_pair[0]] = data_pair[1]
            return data_pair

    def close_async_connection(self, connection_id):
        # При закрытии соединения - мы не закрываем его физически, а всего лишь переносим в свободные.
        # Закрыть можно только зная connection_id, выданный при open_async_connection
        if connection_id in self.used_connections:
            # Вытащить из used_connections
            conn = self.used_connections.pop(connection_id)
            # Поместить во free_connections
            self.free_connections[connection_id] = conn

    def _clean_unused(self):
        # TODO реализовать очистку давно неиспользуемых соединений
        pass

# ==========|АСИНХРОННАЯ ОБВЯЗКА|==========

class AsyncContext(object):
    def __init__(self, factory):
        # Фабрика асинхронных соединений
        self.factory = factory
        # Идентификатор соединения, используемый в пуле
        self.connection_id = None
        # Ссылка на само соединение
        self.connection = None
        # Ссылка на курсор (не факт что понадобится)
        self.cursor = None
        # Функция, вызываемая после успешного выполнения Executor-а
        self.callback = None
        # Данные, используемые в работе Executor-а, хранятся здесь
        self.data = dict()

# Класс, управляющий процессами асинхронного доступа к данным
class PGSQLAsyncExecutor(object):
    # В конструктор передается контекст операции AsyncContext
    def __init__(self, context):
        self.context = context

    def start_processing(self):
        ctx = self.context
        if ctx is not None:
            if ctx.connection is None:
                # Получаем соединение
                conn_pair = ctx.factory.open_async_connection()
                if (conn_pair is not None):
                    # Сохраняем в контексте ID и соединение
                    ctx.connection_id = conn_pair[0]
                    ctx.connection = conn_pair[1]
                    # И начинаем его опрашивать на предмет готовности
                    self.poll_connection()

    # Создаем соединение и опрашиваем его до тех пор, пока оно не будет готово
    def poll_connection(self):
        self._route(self.perform_query, self.poll_connection)

    def perform_query(self):
        # Переопределяется в наследнике. Вызывается, когда соединение готово к выполнению запроса.
        reactor.callLater(0, self.poll_result)

    def poll_result(self):
        self._route(self.result_ready, self.poll_result)

    def result_ready(self):
        # Переопределяется в наследнике. Вызывается, когда запрос выполнен и надо обработать результат
        reactor.callLater(0, self.pass_to_callback)

    def pass_to_callback(self):
        ctx = self.context
        if ctx is not None:
            callback = ctx.callback
            # Закрываем соединение
            ctx.factory.close_async_connection(ctx.connection_id)
            # Передаем управление вызвавшему нас методу, вместе с контекстом
            reactor.callLater(0, callback, ctx)
    
    def _route(self, poll_ok_callback, otherwise_callback):
        ctx = self.context
        if ctx is not None:
            if ctx.connection is not None:
                # Опрашиваем его до тех пор, пока не получим состояние готовности ()
                state = ctx.connection.poll()
                if state == psycopg2.extensions.POLL_OK:
                    reactor.callLater(0, poll_ok_callback)
                else:
                    reactor.callLater(0, otherwise_callback)

# Executor, выполняющий получение объекта из БД
class ContestGetter(PGSQLAsyncExecutor):
    def perform_query(self):
        ctx = self.context
        if ctx is not None:
            conn = ctx.connection
            cursor = conn.cursor()
            ctx.cursor = cursor
            contest_id = ctx.data["contest_id"]
            cursor.execute(SQL_SELECT_CONTEST, (contest_id,))
            # Вызываем perform_query из суперкласса, где происходит передача управления в метод poll_result
            super(ContestGetter, self).perform_query()

    def result_ready(self):
        print "ContestGetter.result_ready for %r" % (self,)
        ctx = self.context
        if ctx is not None:
            cursor = ctx.cursor
            data_row = cursor.fetchone()
            if data_row is not None:
                factory = ContestFactory()
                result = factory.create_contest(
                    data_row[0], 
                    data_row[1],
                    data_row[2], 
                    data_row[3],
                    data_row[4], 
                    data_row[5], 
                    [data_row[6], data_row[7]]
                )
                ctx.data["result"] = result
                # Вызываем result_ready из суперкласса, где происходит передача управления в метод pass_to_callback
                super(ContestGetter, self).result_ready()

# Executor, выполняющий сохранение объекта в БД
class ContestSaver(PGSQLAsyncExecutor):
    def perform_query(self):
        ctx = self.context
        if ctx is not None:
            conn = ctx.connection
            cursor = conn.cursor()
            ctx.cursor = cursor
            contest_id = ctx.data["contest_id"]
            cursor.execute(SQL_SELECT_CONTEST, (contest_id,))
            # Вызываем perform_query из суперкласса, где происходит передача управления в метод poll_result
            super(ContestGetter, self).perform_query()

    def result_ready(self):
        print "ContestGetter.result_ready for %r" % (self,)
        ctx = self.context
        if ctx is not None:
            cursor = ctx.cursor
            data_row = cursor.fetchone()
            if data_row is not None:
                factory = ContestFactory()
                result = factory.create_contest(
                    data_row[0], 
                    data_row[1],
                    data_row[2], 
                    data_row[3],
                    data_row[4], 
                    data_row[5], 
                    [data_row[6], data_row[7]]
                )
                ctx.data["result"] = result
                # Вызываем result_ready из суперкласса, где происходит передача управления в метод pass_to_callback
                super(ContestGetter, self).result_ready()

# ==========|РЕПОЗИТОРИЙ|==========

class PGSQLContestRepository(object):
    implements(IContestRepository)

    def __init__(self, connection_factory):
        self.factory = connection_factory

    def get_by_id(self, contest_id):
        self._get_by_id_callback(contest_id, self._get_by_id_success)

    def _get_by_id_callback(self, contest_id, success_callback):
        # create new execution context
        context = AsyncContext(self.factory)
        # opening new async connection
        conn_ref = self.factory.open_async_connection()
        context.connection_id = conn_ref[0]
        context.connection = conn_ref[1]
        context.data["contest_id"] = contest_id
        context.callback = success_callback
        
        executor = ContestGetter(context)
        reactor.callLater(0, executor.poll_connection)

    def _get_by_id_success(self, context):
        print "_get_by_id_success for %r,%r" % (self, context)
        self.factory.close_async_connection(context.connection_id)
        get_by_id_callback(context.data["result"])

    def save(self, value):
        try:
            if self.connection is not None:
                cursor = self.connection.cursor()
                if value.id is None:
                    cursor.execute(SQL_INSERT_CONTEST, self._params(value))
                    data_row = cursor.fetchone()
                    if data_row is not None:
                        value.id = data_row[0]
                else:
                    cursor.execute(SQL_UPDATE_CONTEST, self._params(value, True))
                self.connection.commit()
            self.record_cache[value.id] = value
            return value
        except Exception as e:
            print "7: %r" % (e,)
            return None
            

    def _params(self, value = None, with_id = False):
        if value is None:
            return ()
        if with_id:
            return (value.title, value.start_time, value.end_time, value.contest_place, 
                    value.contest_country, value.hq_coords[0], value.hq_coords[1], value.id)
        return (value.title, value.start_time, value.end_time, value.contest_place, 
                value.contest_country, value.hq_coords[0], value.hq_coords[1])

# ==========|ЗАПУСК ТЕСТА|==========

def run_test():
    conn_mgr = ConnectionManager()
    print "ConnectionManager created"
    factory = ContestFactory()
    print "ContestFactory created"
    rep = PGSQLContestRepository(conn_mgr)
    print "PGSQLRepository created"
    rep.get_by_id(0)
    rep._get_by_id_callback(0, get_by_id_callback2)
    reactor.callLater(1, rep.get_by_id, 0)
    reactor.callLater(2, rep.get_by_id, 0)
    print "Repository request created"

def get_by_id_callback(result):
    print "result is:"
    print result

def get_by_id_callback2(result):
    print ">>>>>>>>>>>>>>>>>>>"
    print result
    print "<<<<<<<<<<<<<<<<<<<"
    
if __name__ == "__main__":
    reactor.callLater(0, run_test)
    print "Starting reactor"
    reactor.run()
