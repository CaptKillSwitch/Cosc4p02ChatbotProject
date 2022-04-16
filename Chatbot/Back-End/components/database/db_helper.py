import mysql.connector
import pandas as pd
import json


class DbHelper:

    def __init__(self, username, password, output_buffer, host="127.0.0.1"):
        try:
            self.output_buffer = output_buffer
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "busy",
                                               "update_message": "initializing"
                                               }))
            self.__user = username
            self.__password = password
            self.__host = host
            self.__connection = mysql.connector.connect(user=self.__user, password=self.__password, host=self.__host)
            self.__cursor = self.__connection.cursor()
            self.__db_connection = None
            self.__db_cursor = None
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "working",
                                               "update_message": "Initialized"
                                               }))
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Database not initialized, \n system message: {}'.
                                              format(e)
                                               }))

    def get_databases(self):
        try:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "busy",
                                               "update_message": "Getting all databases"
                                               }))
            self.__cursor.execute("SHOW DATABASES")
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "working",
                                               "update_message": "Databases returned"
                                               }))
            return self.__cursor.fetchall()
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Unable to load databases, \n system message: {}'.
                                              format(e)
                                               }))

    def reset_database(self, database_name):
        try:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "busy",
                                               "update_message": "Deleting all current documents"
                                               }))
            self.__cursor.execute("DROP DATABASE IF EXISTS " + database_name)
            self.__cursor.execute("CREATE DATABASE " + database_name)
            self.__cursor.execute("ALTER DATABASE " + database_name + " CHARACTER SET utf8")
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "working",
                                               "update_message": "Documents db reset"
                                               }))
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Failed to reset {}, \n system message: {}'.
                                              format(database_name, e)
                                               }))

    def set_database(self, database_name):
        try:
            self.__db_connection = mysql.connector.connect(user=self.__user, password=self.__password, host=self.__host,
                                                           database=database_name)
            self.__db_cursor = self.__db_connection.cursor()
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Failed to set the database named {}, \n system '
                                                                 'message: {}'.format(database_name, e)
                                               }))

    def __create_table(self, table_name, config):
        try:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "busy",
                                               "update_message": "Creating table " + table_name
                                               }))
            sql_statement = "CREATE TABLE `" + table_name + "` ( " + config + " );"
            if self.__db_connection is not None:
                self.__db_cursor.execute(sql_statement)
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Table {} not created, \n system message: {}'.
                                              format(table_name, e)
                                               }))

    def check_document_info_table(self):
        try:
            self.__create_table("document_info", "`key` VARCHAR(255), `url` VARCHAR(255), `title` VARCHAR(255), "
                                                 "`section_title` VARCHAR(255), PRIMARY KEY(`key`)")
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Unable to create document info table, \n system '
                                                                 'message: {}'.format(e)
                                               }))

    def __insert(self, sql):
        # sanatize
        try:
            self.__db_cursor.execute(sql)
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Insert sql failed for query {}, \n system '
                                                                 'message: {}'.format(sql,e)
                                               }))

    def set_documents(self, documents):
        try:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "busy",
                                               "update_message": "Starting to load documents to the database"
                                               }))
            self.check_document_info_table()
            table_info_sql = "INSERT INTO document_info VALUES ('%s','%s','%s','%s')"
            for key, document in documents.items():
                self.__insert(table_info_sql % (key, document["url"], document["title"], document["section_title"]))
                config = "`id` INT, "
                indicator = "%s, "
                indicator += (len(document["columns"])) * "'%s', "
                for column in document["columns"]:
                    config += "`" + column.replace(" ", "_") + "`" + " VARCHAR(255), "
                config += "PRIMARY KEY (`id`)"
                indicator = indicator[:-2]
                self.__create_table(key, config)
                tuple_id = 0
                insert_sql = "INSERT INTO " + key + " VALUES (" + indicator + ")"
                for value in document["values"]:
                    self.__insert(insert_sql % tuple([tuple_id] + value))
                    tuple_id += 1
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "working",
                                               "update_message": "All documents loaded"
                                               }))
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Failed to set documents \n system '
                                                                 'message: {}'.format(e)
                                               }))

    def get_documents(self):
        try:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "busy",
                                               "update_message": "Getting all documents from the database"
                                               }))
            self.__db_cursor.execute("select * from document_info")
            documents = self.__db_cursor.fetchall()
            ai_documents = {}
            for table_name, url, title, section_title in documents:
                self.__db_cursor.execute("DESCRIBE " + table_name)
                columns = [column[0] for column in self.__db_cursor.fetchall()][1:]
                self.__db_cursor.execute("select * from " + table_name)
                results = [result[1:] for result in self.__db_cursor.fetchall()]
                # do not need the "Id" as it is just an int not req in Ai tables hence [1:]
                ai_documents[table_name] = {
                    "title": title,
                    "section_title": section_title,
                    "url": url,
                    "df": pd.DataFrame(results, columns=columns)
                }
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "working",
                                               "update_message": "Documents returned"
                                               }))
            return ai_documents
        except BaseException as e:
            self.output_buffer.put(json.dumps({"type": "update",
                                               "component": "database",
                                               "update": "error",
                                               "update_message": 'Failed to get documents, \n system '
                                                                 'message: {}'.format(e)
                                               }))
