import datetime
import json
import os
import psycopg2 as dbapi2
import re

from flask import Flask
from flask import redirect
from flask import render_template
from flask.helpers import url_for

app = Flask(__name__)


def get_elephantsql_dsn(vcap_services):
    """Returns the data source name for ElephantSQL."""
    parsed = json.loads(vcap_services)
    uri = parsed["elephantsql"][0]["credentials"]["uri"]
    match = re.match('postgres://(.*?):(.*?)@(.*?)(:(\d+))?/(.*)', uri)
    user, password, host, _, port, dbname = match.groups()
    dsn = """user='{}' password='{}' host='{}' port={}
             dbname='{}'""".format(user, password, host, port, dbname)
    return dsn


@app.route('/', methods=['GET', 'POST'])
def index_page():
    with dbapi2.connect(app.config['dsn']) as connection:
        cursor = connection.cursor()
        query = """SELECT * FROM TARIFF"""
        cursor.execute(query)
        tariffs = cursor.fetchall()
    return render_template('index.html', tariff_list=tariffs)


@app.route('/elements')
def elements_page():
    with dbapi2.connect(app.config['dsn']) as connection:
        cursor = connection.cursor()
        query = """SELECT * FROM TARIFF"""
        cursor.execute(query)
        tariffs = cursor.fetchall()

        query = """SELECT * FROM CAMPAIGN"""
        cursor.execute(query)
        campaigns = cursor.fetchall()
    return render_template('elements.html', tariff_list=tariffs, campaign_list=campaigns)


@app.route('/initdb')
def initialize_database():
    with dbapi2.connect(app.config['dsn']) as connection:
        cursor = connection.cursor()

        # First I delete all the tables.
        query = """DROP TABLE IF EXISTS TARIFF, CUSTOMER, CONTRACT, ADDRESS, CAMPAIGN, CAMPAIGN_MSISDN, BALANCE, MSISDN, WALLET, COUNTER"""
        cursor.execute(query)


        ### Now, I will add all the tables.
        query = """CREATE TABLE TARIFF (
                                         id SERIAL,
                                         name VARCHAR(50) NOT NULL,
                                         description VARCHAR(255) NOT NULL,
                                         price INTEGER NOT NULL,
                                         data INTEGER NOT NULL,
                                         voice INTEGER NOT NULL,
                                         sms INTEGER NOT NULL,
                                         CHECK((price >= 0) AND (data >= 0) AND (voice >= 0) AND (sms >= 0)),
                                         PRIMARY KEY (id)
                                        )"""
        cursor.execute(query)

        query = """CREATE TABLE CUSTOMER (
                                           id SERIAL,
                                           name VARCHAR(50) NOT NULL,
                                           surname VARCHAR(50) NOT NULL,
                                           birth_date DATE NOT NULL,
                                           PRIMARY KEY (id)
                                          )"""
        cursor.execute(query)

        query = """CREATE TABLE CONTRACT (
                                           id SERIAL,
                                           secret_question VARCHAR(255) NOT NULL,
                                           secret_answer VARCHAR(255) NOT NULL,
                                           customer_id INTEGER NOT NULL,
                                           PRIMARY KEY (id),
                                           FOREIGN KEY (customer_id) REFERENCES CUSTOMER(id) ON DELETE CASCADE ON UPDATE CASCADE
                                          )"""
        cursor.execute(query)

        query = """CREATE TABLE ADDRESS (
                                           id SERIAL,
                                           name VARCHAR(50) NOT NULL,
                                           description VARCHAR(255) NOT NULL,
                                           contract_id INTEGER NOT NULL,
                                           PRIMARY KEY (id),
                                           FOREIGN KEY (contract_id) REFERENCES CONTRACT(id) ON DELETE CASCADE ON UPDATE CASCADE
                                          )"""
        cursor.execute(query)

        query = """CREATE TABLE CAMPAIGN (
                                           id SERIAL,
                                           name VARCHAR(50) NOT NULL,
                                           description VARCHAR(255) NOT NULL,
                                           rule VARCHAR(255) NOT NULL,
                                           PRIMARY KEY (id)
                                          )"""
        cursor.execute(query)

        query = """CREATE TABLE BALANCE (
                                           id SERIAL,
                                           remaining_data INTEGER NOT NULL,
                                           remaining_voice INTEGER NOT NULL,
                                           remaining_sms INTEGER NOT NULL,
                                           msisdn_id INTEGER NOT NULL,
                                           contract_id INTEGER NOT NULL,
                                           CHECK((remaining_data >= 0) AND (remaining_voice >= 0) AND (remaining_sms >= 0)),
                                           PRIMARY KEY (id),
                                           FOREIGN KEY (contract_id) REFERENCES CONTRACT(id) ON DELETE CASCADE ON UPDATE CASCADE
                                          )"""
        cursor.execute(query)

        query = """CREATE TABLE MSISDN (
                                          id SERIAL,
                                          msisdn_number VARCHAR(11) NOT NULL,
                                          password VARCHAR(22) NOT NULL,
                                          activation_date DATE NOT NULL DEFAULT CURRENT_DATE,
                                          contract_id INTEGER NOT NULL,
                                          balance_id INTEGER NOT NULL,
                                          tariff_id INTEGER NOT NULL,
                                          PRIMARY KEY (id),
                                          FOREIGN KEY (contract_id) REFERENCES CONTRACT(id) ON DELETE CASCADE ON UPDATE CASCADE,
                                          FOREIGN KEY (balance_id) REFERENCES BALANCE(id) ON DELETE CASCADE ON UPDATE CASCADE,
                                          FOREIGN KEY (tariff_id) REFERENCES TARIFF(id) ON DELETE CASCADE ON UPDATE CASCADE
                                         )"""
        cursor.execute(query)

        query = """CREATE TABLE CAMPAIGN_MSISDN (
                                                 msisdn_id INTEGER NOT NULL,
                                                 campaign_id INTEGER NOT NULL,
                                                 FOREIGN KEY (msisdn_id) REFERENCES MSISDN(id) ON DELETE CASCADE ON UPDATE CASCADE,
                                                 FOREIGN KEY (campaign_id) REFERENCES CAMPAIGN(id) ON DELETE CASCADE ON UPDATE CASCADE
                                                 )"""
        cursor.execute(query)

        query = """CREATE TABLE WALLET (
                                         id SERIAL,
                                         amount INTEGER NOT NULL,
                                         customer_id INTEGER NOT NULL,
                                         PRIMARY KEY (id),
                                         FOREIGN KEY (customer_id) REFERENCES CUSTOMER(id) ON DELETE CASCADE ON UPDATE CASCADE
                                        )"""
        cursor.execute(query)


        ### I insert some data to the TARIFF table.
        query = """INSERT INTO TARIFF(name, description, price, data, voice, sms)
                               VALUES('STUDENT PACK', 'Genclere ozel tarife. Her yone 500 dk konusma, 1000 sms ustelik 2 gb internet aylik sadece 20 TL', 20, 2048, 500, 1000);


                   INSERT INTO TARIFF(name, description, price, data, voice, sms)
                                VALUES('BUSINESS PACK', 'Bana hicbir sey yetmiyor diyenlere ozel tarife. Her yone 2000 dk konusma, 5000 sms ve 16 gb internet aylik 50 TL', 50, 16384, 2000, 5000);


                   INSERT INTO TARIFF(name, description, price, data, voice, sms)
                                VALUES('ECONOMY PACK', 'Herkes kesime hitap eden hesapli tarife. Her yone 250 dk konusma, 500 sms ve 1 gb internet sadece aylik 15 TL', 15, 1024, 250, 500);


                   INSERT INTO TARIFF(name, description, price, data, voice, sms)
                                VALUES('USER PACK', 'Ben sadece konusma paketi istiyorum diyorsaniz bu tarife tam size gore. Her yone 2500 dk konusma ve 1 gb internet aylik 20 TL', 20, 1024, 2500, 0)"""
        cursor.execute(query)

        ### I insert some data to the CUSTOMER table.
        query = """ INSERT INTO CUSTOMER(name, surname, birth_date)
                                VALUES('Natalie', 'Boyd', '1987-11-09');

                    INSERT INTO CUSTOMER(name, surname, birth_date)
                        VALUES('Rudy', 'Wells', '1992-04-11');

                    INSERT INTO CUSTOMER(name, surname, birth_date)
                        VALUES('Gabriel', 'Jacobs', '1965-02-14');

                    INSERT INTO CUSTOMER(name, surname, birth_date)
                        VALUES('Lynne', 'Warren', '1981-04-17')"""
        cursor.execute(query)

        ### I insert some data to the CONTRACT table.
        query = """ INSERT INTO CONTRACT(secret_question, secret_answer, customer_id)
                        VALUES('First school?', 'I dont remember', 1);

                    INSERT INTO CONTRACT(secret_question, secret_answer, customer_id)
                        VALUES('Favorite fruite?', 'Banana', 2);

                    INSERT INTO CONTRACT(secret_question, secret_answer, customer_id)
                        VALUES('Favorite Band?', 'The Beatles', 3);

                    INSERT INTO CONTRACT(secret_question, secret_answer, customer_id)
                        VALUES('What is your first teacher name?', 'Barny', 4)"""
        cursor.execute(query)

        ### I insert some data to the CAMPAIGN table.
        query = """ INSERT INTO CAMPAIGN(name, description, rule)
                    VALUES('FOR NEWS PACK', 'This campaign for the new customers. 1000 MIN, 2000 SMS and 4 GB internet.', 'To use this campaign, you should be new customer.');

                    INSERT INTO CAMPAIGN(name, description, rule)
                    VALUES('ADVANTAGE PACK', 'This campaign for the customers who transfer CS-CELL from another one. 2000 MIN, 5000 SMS, 6 GB internet.', 'To use this campaign, you should be transferred to CS-CELL from another company.');

                    INSERT INTO CAMPAIGN(name, description, rule)
                    VALUES('COUPLE PACK', 'This campaign for the customers who are married. 750 MIN, 1500 SMS, 6 GB internet.', 'To use this campaign, you should be married.')"""
        cursor.execute(query)

        ### I insert some data to the ADDRESS table.
        query = """ INSERT INTO ADDRESS(name, description, contract_id)
                        VALUES('Ev', 'Beylikduzu - Istanbul', 1);

                    INSERT INTO ADDRESS(name, description, contract_id)
                        VALUES('Is', 'Maslak - Istanbul', 1);

                    INSERT INTO ADDRESS(name, description, contract_id)
                        VALUES('Is', 'Etimesgut - Ankara', 2);

                    INSERT INTO ADDRESS(name, description, contract_id)
                        VALUES('Ev', 'Harran - Sanliurfa', 3);

                    INSERT INTO ADDRESS(name, description, contract_id)
                        VALUES('Is', 'Didim - Aydin', 3);

                    INSERT INTO ADDRESS(name, description, contract_id)
                        VALUES('Ev', 'Bahcelievler - Istanbul ', 4)"""
        cursor.execute(query)

        ### I insert some data to the WALLET table.
        query = """ INSERT INTO WALLET(amount, customer_id)
                        VALUES(50, 2);

                    INSERT INTO WALLET(amount, customer_id)
                        VALUES(75, 3);

                    INSERT INTO WALLET(amount, customer_id)
                        VALUES(100, 4);

                    INSERT INTO WALLET(amount, customer_id)
                        VALUES(60, 1)"""
        cursor.execute(query)

        ### I insert some data to the BALANCE table.
        query = """ INSERT INTO BALANCE(remaining_data, remaining_voice, remaining_sms, msisdn_id, contract_id)
                        VALUES(730, 720, 656, 0, 1);

                    INSERT INTO BALANCE(remaining_data, remaining_voice, remaining_sms, msisdn_id, contract_id)
                        VALUES(1234, 21, 4843, 0, 2);

                    INSERT INTO BALANCE(remaining_data, remaining_voice, remaining_sms, msisdn_id, contract_id)
                        VALUES(325, 452, 123, 0, 3);

                    INSERT INTO BALANCE(remaining_data, remaining_voice, remaining_sms, msisdn_id, contract_id)
                        VALUES(562, 142, 534, 0, 4)"""
        cursor.execute(query)

        ### I insert some data to the MSISDN table.
        query = """ INSERT INTO MSISDN(msisdn_number, password, contract_id, balance_id, tariff_id)
                        VALUES('11111111111', 'deneme', 1, 4, 1);

                    INSERT INTO MSISDN(msisdn_number, password, contract_id, balance_id, tariff_id)
                        VALUES('22222222222', 'deneme', 2, 3, 2);

                    INSERT INTO MSISDN(msisdn_number, password, contract_id, balance_id, tariff_id)
                        VALUES('33333333333', 'deneme', 3, 2, 3);

                    INSERT INTO MSISDN(msisdn_number, password, contract_id, balance_id, tariff_id)
                        VALUES('44444444444', 'deneme', 4, 1, 4)"""
        cursor.execute(query)

        ### I insert some data to the CAMPAIGN_MSISDN table.
        query = """ INSERT INTO CAMPAIGN_MSISDN(msisdn_id, campaign_id)
                        VALUES(1, 1);

                    INSERT INTO CAMPAIGN_MSISDN(msisdn_id, campaign_id)
                        VALUES(2, 2);

                    INSERT INTO CAMPAIGN_MSISDN(msisdn_id, campaign_id)
                        VALUES(3, 2);

                    INSERT INTO CAMPAIGN_MSISDN(msisdn_id, campaign_id)
                        VALUES(4, 1)"""
        cursor.execute(query)


        ### I updated some data in the BALANCE table and add a FOREIGN KEY.
        query = """ UPDATE BALANCE
                        SET msisdn_id = 1
                        WHERE id = 4;

                    UPDATE BALANCE
                        SET msisdn_id = 2
                        WHERE id = 3;

                    UPDATE BALANCE
                        SET msisdn_id = 3
                        WHERE id = 2;

                    UPDATE BALANCE
                        SET msisdn_id = 4
                        WHERE id = 1;

                    ALTER TABLE BALANCE
                        ADD CONSTRAINT fk_balance_msisdn_id
                        FOREIGN KEY (msisdn_id)
                        REFERENCES MSISDN(id)
                        ON DELETE CASCADE ON UPDATE CASCADE"""
        cursor.execute(query)


        connection.commit()
    return redirect(url_for('index_page'))


if __name__ == '__main__':
    VCAP_APP_PORT = os.getenv('VCAP_APP_PORT')
    if VCAP_APP_PORT is not None:
        port, debug = int(VCAP_APP_PORT), False
    else:
        port, debug = 5000, True

    VCAP_SERVICES = os.getenv('VCAP_SERVICES')
    if VCAP_SERVICES is not None:
        app.config['dsn'] = get_elephantsql_dsn(VCAP_SERVICES)
    else:
        app.config['dsn'] = """user='vagrant' password='vagrant'
                               host='localhost' port=5432 dbname='itucsdb'"""

    app.run(host='0.0.0.0', port=port, debug=debug)
