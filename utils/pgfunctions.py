import psycopg2
import sys
import calendar
import time
from sqlalchemy import create_engine
import pandas as pd
from utils.stock_settings import Settings
from utils import stock_csv_functions as csv
from utils import stock_other_functions as oth
from utils import stock_time as myt
from io import StringIO
from utils import stock_time as st

output = StringIO()

"""
There are the functions about database.
Connect to database.
Execute a SQL.
Query column in one table.
Query the max timestamp in one table.
Clear one table's data.
Import CSV to database by copy_from.
Import CSV to database by to_sql.
Import tuples to database by SQL.
"""


stock_settings = Settings()
PARAM_DIC = stock_settings.PARAM_DIC


def connect():
    """
    Connect to the PostgreSQL database server.
    :return: conn or None
    """
    try:
        conn = psycopg2.connect(**PARAM_DIC)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"error:{error},PARAM_DIC:{PARAM_DIC}")
        oth.log(error)
        oth.send_sms(f"conn has an error:{error}")
        sys.exit(1)
        return None
    return conn


def execute_sql(sql):
    """
    Query any sql in one table
    :param sql: str
    :return: results:  list,但是类似含有元祖的列表，格式类似[('A',), ('AA',), ('AAAIF',), ('AAALF',)]
    要得到这个最后的每个数值，你就得例如return_value[0][0]
    """
    conn_db = connect()
    cursor = conn_db.cursor()
    try:
        cursor.execute(sql)
    except Exception as error:
        print(f"error:{error}")
        oth.log(error)
        cursor.close()
        conn_db.close()
        return None
    results = cursor.fetchall()
    conn_db.commit()
    cursor.close()
    conn_db.close()
    return results


def execute_sql_not_return(sql):
    """
    Query any sql in one table. But if sql is ok and not record, it also will return True.
    :param sql: str
    :return: results:data or None
    """
    conn_db = connect()
    cursor = conn_db.cursor()
    try:
        cursor.execute(sql)
    except Exception as error:
        print(f"error:{error}")
        cursor.close()
        conn_db.close()
        return False
    conn_db.commit()
    cursor.close()
    conn_db.close()
    return True


def execute_insert_sql(sql):
    """
    Query any sql to insert data to table
    :param sql: str
    :return: results:data or None
    """
    conn_db = connect()
    cursor = conn_db.cursor()
    try:
        cursor.execute(sql)
    except Exception as error:
        print(f"error:{error}")
        oth.log(error)
        cursor.close()
        conn_db.close()
        return None
    conn_db.commit()
    cursor.close()
    conn_db.close()

def column(table, col):
    """
    Query column in one table
    :param table: str
    :param col: str
    :return: pg_column_dt:,list that includes tuple,such as [('MCB3208',), ('MCB3228',), ('MCB3248',), ('MCB3258',)]
    """
    try:
        conn_db = connect()
    except IOError as error:
        print(f"There is an IO error when connecting to the database.{error}")
        oth.log(error)
        return None
    cursor = conn_db.cursor()
    sql = f"select {col} from  {table} order by {col} "
    try:
        cursor.execute(sql)
    except (Exception, psycopg2.errors.SyntaxError) as error:
        oth.log(error)
        cursor.close()
        conn_db.close()
        return None
    results = cursor.fetchall()
    if results == []:
        print(f"The {table} is empty")
        pg_column_dt = None
    else:
        pg_column_dt = results  # this is a list
    conn_db.commit()
    cursor.close()
    conn_db.close()
    return pg_column_dt


def max_t(table, symbol_name):
    """
    Query the max timestamp in one table
    :param table: str
    :param symbol_name: str
    :return: pg_max_dt:int
    """
    try:
        conn_db = connect()
    except IOError as error:
        print("There is an IO error when connecting to the database.")
        oth.log(error)
        return None
    cursor = conn_db.cursor()
    sql = f"select * from {table} where symbol='{symbol_name}' order by series desc limit 1"
    cursor.execute(sql)
    results = cursor.fetchall()
    # print (results)
    if results == []:
        # print ("empety table")
        pg_max_dt = 0
    else:
        pg_max_dt = results[0][6]
    conn_db.commit()
    cursor.close()
    conn_db.close()
    return pg_max_dt



def clear_table(table):
    """
    Clear one table's data
    :param table: str
    :return: 1 or None
    """
    try:
        conn_db = connect()
    except IOError as error:
        print("There is an IO error when connecting to the database.")
        oth.log(error)
        return None
    cur = conn_db.cursor()
    sql = f"delete from {table} where 1=1"
    try:
        cur.execute(sql)
    except(Exception, psycopg2.DatabaseError) as error:
        oth.log(error)
        cur.close()
        conn_db.close()
        return None
    conn_db.commit()
    cur.close()
    conn_db.close()
    print("Clear table done.")
    return 1


def pg_to_sql(table, path, columns, symbol=""):
    """
    Import dataset to PostregSQL.very fast than old version.
    :param table: str
    :param path: str
    :param columns: list
    :param symbol: str
    :return: 1 or None
    """
    # print("Begin import data.")
    begin_time = time.time()
    f = open(path, 'r')
    conn = connect()
    cursor = conn.cursor()
    # 使用copy_from 数据必须是无标题
    try:
        cursor.copy_from(f, table, sep=",", columns=columns)
        conn.commit()
    except psycopg2.errors.InvalidTextRepresentation as error:
        print(f"Invalid input syntax for type:{error}. Symbol:{symbol}. But pass to continue.")
        oth.log(error, symbol)
        conn.rollback()
        cursor.close()
        csv.clear_csv(path)
        return None
    except psycopg2.DatabaseError as error:
        # clear_csv(path)
        print(f"Import database error:{error}.Symbol:{symbol}")
        oth.log(error, symbol)
        conn.rollback()
        cursor.close()
        csv.clear_csv(path)
        return None
    except Exception as error:
        print(f"Import error:{error}.Symbol:{symbol}")
        oth.log(error, symbol)
        conn.rollback()
        cursor.close()
        csv.clear_csv(path)
        return None
    cursor.close()
    end_time = time.time()
    # print(f"Import to database cost :{round(end_time-begin_time, 2)}")
    csv.clear_csv(path)
    return 1


def pg_to_sql_company_profile(table, path, symbol=""):
    """
    Only used by import company profile data to database.
    :param table: str
    :param path: str
    :param symbol: str
    :return: 1 or None
    """
    csv.add_csv_title(path, stock_settings.profile_title)
    print(path)
    dataset = pd.read_csv(path)
    begin_time = time.time()
    pq_info = "postgresql+psycopg2://"+PARAM_DIC["user"]+":"+PARAM_DIC["password"]+"@"+PARAM_DIC["host"]+"/"+PARAM_DIC["database"]
    engine = create_engine(pq_info)
    try:
        dataset.to_sql(table, engine, index=False, chunksize=None, if_exists='append', method="multi")
    except (Exception) as error:
        print(f"Company profile to_sql error:{error}")
        oth.log(error, symbol)
        return None
    csv.clear_csv(path)
    end_time = time.time()
    # print("Import to database cost :%.2f " % round(end_time-begin_time, 2))
    return 1


def df_db(table, df):
    """
    This function's old name is insert7
    Import dataframe to the table of Postgres database.
    Tips: the columns of the df mush all match the columns of this table. Otherwise will be fail.
    :param table: str
    :param df: dataframe
    :return: 1 or None
    """
    # Using cursor.executemany() to insert the dataframe
    # Create a list of tuples from the dataframe values
    tuples = [tuple(x) for x in df.to_numpy()]
    # Comma-separated dataframe columns
    cols = ','.join(list(df.columns))
    len_cols = len(list(df.columns))
    col_str = ""
    for i in range(len_cols):
        if i == 0:
            col_str = col_str + "%%s"
        else:
            col_str = col_str + ",%%s"
    sql_str = "INSERT INTO %s(%s) VALUES("+col_str+")"
    query = sql_str % (table, cols)
    conn = connect()
    cur = conn.cursor()
    try:
        cur.executemany(query, tuples)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        oth.log(error)
        conn.rollback()
        cur.close()
        return None
    print("execute_many() done")
    cur.close()
    return 1


def database_to_pd(sql):
    """
    输入SQL查询语句，用pandaframe来得到pd数据集格式的查询结果
    :param sql: str 字符串
    :return: pd格式的数据集
    """
    conn = connect()
    results = pd.read_sql(sql, conn)
    conn.close()
    return results


def get_symbol_df(symbol_list, start_date: int, end_date: int):
    """
    输入起始和终止日期，拿到这期间内得的全部的股票的清单，返回DataFrame数据集。
    因为并非所有股票在这个日期期间内都有，有的股票或许已经退市了，有的或许这期间还没上市。
    :param start_date: int 格式是20200601
    :param end_date: int  格式是20201228
    :return: DataFrame
    """
    st = myt.dateint_stamp(start_date, "begin")
    et = myt.dateint_stamp(end_date, "end")
    # sql = f"select distinct symbol from stock_candles_day where t>{st} and t<{et} and c>0"
    a = "("
    for i in symbol_list:
        a = a + "\'" + i + "\'" + ","
    a = a[0:len(a) - 1]
    a = a + ")"
    sql = f"select distinct symbol from stock_candles_day where t>{st} and t<{et} and c>0 and symbol in {a} "
    conn = connect()
    stock_list_result = pd.read_sql(sql, conn)
    conn.close()
    return stock_list_result


def find_valid_symbol_bymodel():
    """
    找到一些近期数据可以符合交易模型的股票，返回一个股票名字的列表。
    模型是每日更新，靠每日执行stock_gentic_main.py
    缺点：写死了查询近期数据的日期，这需要未来改。只返回15个股票，也要改。增加了15天宽裕数据，也考虑改。
    """
    sql = "select algorithm from stock_algorithm order by create_date desc limit 1 "
    algorithm = eval((execute_sql(sql))[0][0])
    sql = "select distinct(symbol) from stock_candles_day "\
            "where extract(day from dt)=1 and  extract(year from dt)=2021 and  extract(month from dt)=4 and c>150 limit 15 "
    symbol_df = database_to_pd(sql)
    valid_symbol_list = []
    for symbol in list(symbol_df["symbol"]):
        t_stamp = st.dateint_stamp(
            st.add_dateint(int(int(time.strftime('%Y%m%d'))), ~(sum(algorithm) + 15) + 1))  # 从当前日期往前推N天拿到宽裕的数据集
        sql = f"select c,t,dt,symbol from stock_candles_day where symbol='{symbol}' and t>{t_stamp} order by t desc  "
        df = database_to_pd(sql)
        # print(df)
        price = {}
        a = algorithm
        a.reverse()
        for i in range(len(a)):
            b = sum(a[1:1 + i])
            price[i] = df['c'].iloc[b]
            # print(f"D{i}的价格是=={price[i]}")
        b = True
        max = price[0]
        for i in range(len(a) - 1):
            if price[i + 1] < max:
                max = price[i + 1]
            else:
                b = False
                break
        if b is True:
            # print(f"这个股票符合模型，接下来的{algorithm[-1]}天内可能会有机会")
            valid_symbol_list.append(symbol)
        else:
            # print(f"这个股票不符合模型对应要求，放弃，找其他股票")
            pass
    # print(f"=这些股票可以考虑交易{valid_symbol_list}")
    return valid_symbol_list


def df_columns_db(table, df, columns):
    """
    Import dataframe's some columns to the table's some columns of Postgres database.
    Tips: the columns of the df mush all match the columns of this table, and the columns must are same.
    :param table: str
    :param df: dataframe
    :param columns: list
    :return: 1 or None
    """
    list_b = []
    for index, rows in df.iterrows():
        list_a = []
        for column_name in columns:
            value = rows[column_name]
            list_a.append(value)
        list_b.append(list_a)
    col_str = ""
    for i in range(len(columns)):
        if i == 0:
            col_str = col_str + "%s"
        else:
            col_str = col_str + ",%s"
    a = ",".join(columns)
    query = f"INSERT INTO {table}({a}) VALUES(" + col_str + ")"
    conn = connect()
    cur = conn.cursor()
    try:
        cur.executemany(query, list_b)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        oth.log(error)
        conn.rollback()
        cur.close()
        return None
    # print("execute_many() done")
    cur.close()
    return 1

def whether_data(table, wh):
    """
    query whether has record in the table
    :param table: str   table name such as 'clients'
    :param wh: str    query requirement such as  'id=1 and year>2010'
    :return: True or False    True meaning existence record, False meaning no record
    """
    sql = f'select count(*) from {table} where {wh}'
    result = execute_sql(sql)
    if result[0][0] == 0:
        return False
    else:
        return True

def get_new_df(table, df, condition):
    """
    query whether has duplex data between table and dataframe.
    if has duplex data, delete them in the dataframe and return a new dataframe
    :param table: str   table name such as 'fund_price'
    :param df: dataframe
    :param condition: list   the columns be used to compare between the table and the dataframe
    :return: dataframe      df_result,only has the new daily price
    """
    str1 = ""
    str2 = ""
    j = 0
    for i in condition:
        record_max = df[i].max()
        record_min = df[i].min()
        if j == 0:
            str1 = i
            str2 = f"{i}>='{record_min}' and {i}<='{record_max}' "
        else:
            str1 = str1 + "," + i
            str_temp = f"{i}>='{record_min}' and {i}<='{record_max}' "
            str2 = str2 + "and " + str_temp
        j += 1
    if whether_data(table, str2):
        sql = f"select {str1} from {table} where {str2} "
        df_db = database_to_pd(sql)
        for i in condition:
            if i == "date":
                df_db["date"] = pd.to_datetime(df_db["date"])
        df_result = df.merge(df_db, how="left", left_on=condition,
                             right_on=condition, indicator='i').query("i=='left_only'")
        df_result.drop('i', axis=1, inplace=True)
    else:
        df_result = df
    return df_result
