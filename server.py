import datetime
import json
import os
import psycopg2 as dbapi2
import re

from flask import Flask
from flask import redirect
from flask import request
from flask import session
from flask import render_template
from flask.helpers import url_for
from pip._vendor.requests.api import post

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

        query = """SELECT * FROM CAMPAIGN"""
        cursor.execute(query)
        campaigns = cursor.fetchall()
    return render_template('index.html', tariff_list=tariffs, campaign_list=campaigns)


@app.route('/user', methods=['GET', 'POST'])
def user_page():
    uid = request.args['user_information']
    with dbapi2.connect(app.config['dsn']) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM CUSTOMER WHERE ID = (SELECT CUSTOMER_ID FROM CONTRACT WHERE ID = (SELECT CONTRACT_ID FROM MSISDN WHERE ID = '%s'))"%uid)
        user = cursor.fetchall()

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM WALLET WHERE CUSTOMER_ID = (SELECT ID FROM CUSTOMER WHERE ID = (SELECT CUSTOMER_ID FROM CONTRACT WHERE ID = (SELECT CONTRACT_ID FROM MSISDN WHERE ID = '%s')))"%uid)
        wallet = cursor.fetchall()

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM ADDRESS WHERE CONTRACT_ID = (SELECT CONTRACT_ID FROM MSISDN WHERE ID = '%s')"%uid)
        address = cursor.fetchall()

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM BALANCE WHERE MSISDN_ID = '%s'"%uid)
        balance = cursor.fetchall()

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM TARIFF WHERE ID = (SELECT TARIFF_ID FROM MSISDN WHERE ID = '%s')"%uid)
        tariff = cursor.fetchall()

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM CAMPAIGN WHERE ID = (SELECT campaign_id FROM CAMPAIGN_MSISDN WHERE msisdn_id = '%s')"%uid)
        campaign = cursor.fetchall()

    print(user)
    print(wallet)
    print(address)
    print(balance)
    print(tariff)
    print(campaign)
    return render_template('user_page.html', user=user, wallet=wallet, address=address, balance=balance, tariff=tariff, campaign=campaign)


@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    return render_template('admin.html')


@app.route('/customer_list', methods=['GET', 'POST'])
def customer_list_page():
    with dbapi2.connect(app.config['dsn']) as connection:
        cursor = connection.cursor()
        query = """SELECT * FROM CUSTOMER"""
        cursor.execute(query)
        customers = cursor.fetchall()

    return render_template('customer_list.html', customers=customers)


@app.route('/customer_add', methods=['GET', 'POST'])
def customer_add_page():
    info = None
    if request.method == 'POST':
        Name = request.form['name']
        Surname = request.form['surname']
        Birth_date = request.form['birth_date']

        if (Name == '') & (Surname == '') & (Birth_date == ''):
            info = 'Please fill blank areas.'
        elif (Name == '') & (Surname == ''):
            info = 'Please enter name and surname.'
        elif (Name == '') & (Birth_date == ''):
            info = 'Please enter name and birth date.'
        elif (Surname == '') & (Birth_date == ''):
            info = 'Please enter surname and birth date.'
        elif (Name == '') & (Birth_date == ''):
            info = 'Please enter name and birth date.'
        elif Name == '':
            info = 'Please enter name.'
        elif Surname == '':
            info = 'Please enter surname.'
        elif Birth_date == '':
            info = 'Please enter birth date.'
        else:
            with dbapi2.connect(app.config['dsn']) as connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO CUSTOMER(name, surname, birth_date) VALUES ('%s', '%s', '%s')"%(Name, Surname, Birth_date))
                connection.commit()
                info = "Customer added successfully."

    return render_template('customer_add.html', info=info)


@app.route('/customer_update', methods=['GET', 'POST'])
def customer_update_page():
    info = None
    if request.method == 'POST':
        ID = request.form['id']
        Name = request.form['name']
        Surname = request.form['surname']
        Birth_date = request.form['birth_date']

        if (ID == '') | (Name == '') | (Surname == '') | (Birth_date == ''):
            info = 'Please fill blank areas.'
        else:
            with dbapi2.connect(app.config['dsn']) as connection:
                cursor = connection.cursor()
                cursor.execute("UPDATE CUSTOMER SET name = '%s', surname = '%s',  birth_date = '%s' WHERE id = '%s'"%(Name, Surname, Birth_date, ID))
                connection.commit()
                info = "Customer updated successfully."

    return render_template('customer_update.html', info=info)


@app.route('/customer_delete', methods=['GET', 'POST'])
def customer_delete_page():
    info = None
    if request.method == 'POST':
        ID = request.form['id']

        if (ID == ''):
            info = 'Please enter customer id.'
        else:
            with dbapi2.connect(app.config['dsn']) as connection:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM CUSTOMER WHERE id = '%s'"%ID)
                connection.commit()
                info = "Customer deleted successfully."

    return render_template('customer_delete.html', info=info)


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in_page():
    with dbapi2.connect(app.config['dsn']) as connection:
        cursor = connection.cursor()
        query = """SELECT msisdn_number, password FROM MSISDN"""
        cursor.execute(query)
        users = cursor.fetchall()

        query = """SELECT * FROM CUSTOMER"""
        cursor.execute(query)
        adminInfo = cursor.fetchall()

    error = None
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        password = request.form['password']
        exists = False
        is_admin = False

        if phone_number == adminInfo[4][1] and password == adminInfo[4][2]:
            is_admin = True

        for row in users:
            if phone_number == row[0] and password == row[1]:
                exists = True

        if is_admin == True:
            return redirect(url_for('admin_page'))
        else:
            if exists == False:
                error = 'Invalid Credentials. Please try again.'
                print('Error : ', error)
            else:
                with dbapi2.connect(app.config['dsn']) as connection:
                    cursor = connection.cursor()

                    cursor.execute("SELECT id FROM MSISDN WHERE msisdn_number='%s'"%phone_number)
                    data = cursor.fetchall()

                user_information = data[0][0]
                print('MSISDN id : ', user_information)

                return redirect(url_for('user_page', user_information=user_information))

    try:
        print("try")
        return render_template('sign_in.html', error=error)
    except:
        print("expect")
        return render_template('sign_in.html', error=error)


@app.route('/remember', methods=['GET', 'POST'])
def remember_page():
    error = None
    user_password = None
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        secret_question = request.form['secret_question']
        secret_answer = request.form['secret_answer']

        if (phone_number == '') & (secret_question == '') & (secret_answer == ''):
            error = 'Please fill blank areas.'
        elif (phone_number == '') & (secret_question == ''):
            error = 'Please enter your phone_number and secret_question.'
        elif (phone_number == '') & (secret_answer == ''):
            error = 'Please enter your phone_number and secret_answer.'
        elif (secret_question == '') & (secret_answer == ''):
            error = 'Please enter your secret_question and secret_answer.'
        elif secret_question == '':
            error = 'Please enter your secret_question.'
        elif secret_answer == '':
            error = 'Please enter your secret_answer.'
        elif phone_number == '':
            error = 'Please enter your phone number.'
        else:
            with dbapi2.connect(app.config['dsn']) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT secret_question, secret_answer FROM CONTRACT WHERE id = (SELECT contract_id FROM MSISDN WHERE msisdn_number='%s')"%phone_number)
                data = cursor.fetchall()

                matched = False
                for row in data:
                    if secret_question == row[0] and secret_answer == row[1]:
                        matched = True

                if matched == False:
                    error = 'Invalid information. Please try again.'
                else:
                    with dbapi2.connect(app.config['dsn']) as connection:
                        cursor = connection.cursor()
                        cursor.execute("SELECT password FROM MSISDN WHERE msisdn_number='%s'"%phone_number)
                        password = cursor.fetchall()

                    error = None
                    user_password = password[0][0]
    return render_template('remember.html', error=error, user_password=user_password)


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
                        VALUES('Lynne', 'Warren', '1981-04-17');

                    INSERT INTO CUSTOMER(name, surname, birth_date)
                        VALUES('Admin', '123456', '1991-06-09')"""
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
                        VALUES(730, 720, 0, 0, 1);

                    INSERT INTO BALANCE(remaining_data, remaining_voice, remaining_sms, msisdn_id, contract_id)
                        VALUES(722, 21, 443, 0, 2);

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
