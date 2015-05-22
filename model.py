""" Module for database models used in main.py of andrea-shinnigan"""

import datetime
import hmac
import string
import random
import re

from google.appengine.ext import db

SECRET = "wobje"  # salt for id hash

# Regular expressions for valid username, password, and email
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PW_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")


class Account(db.Model):
    """Database model for accounts of the users"""
    username = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    email = db.StringProperty()

    @classmethod
    def _check_username(cls, username):
        """Check validity of a username"""
        return USER_RE.match(username)

    @classmethod
    def _check_password(cls, password):
        """Check validity of a password"""
        return PW_RE.match(password)

    @classmethod
    def _check_verify(cls, password, verify):
        """Check if password verification matches password"""
        return password and verify == password

    @classmethod
    def _check_email(cls, email):
        """Check validity of an email"""
        if email:
            return EMAIL_RE.match(email)
        else:
            return True

    @classmethod
    def check_account(cls, name):
        """Check if an account with a username exists"""
        username = cls.all().filter('username = ', name).get()
        if username:
            return username
        else:
            return False

    @classmethod
    def signup_verify(cls, username, password, verify, email):
        """Check validity of a username, password, password verification,
        email, and an account with the username already exists"""
        username_flag = cls._check_username(username)
        password_flag = cls._check_password(password)
        verify_flag = cls._check_verify(password, verify)
        email_flag = cls._check_email(email)
        account_flag = cls.check_account(username)

        # Dictionary is used to store error flags of which signup
        # information submitted is invalid
        error_params = dict(username_flag=username_flag,
                            password_flag=password_flag,
                            verify_flag=verify_flag,
                            email_flag=email_flag,
                            account_flag=account_flag)

        return error_params

    # Below class functions are used for account hashing
    @classmethod
    def make_salt(cls):
        """Make salt to store password"""
        return ''.join(random.choice(string.letters) for x in range(5))

    @classmethod
    def make_hash(cls, password, salt=False):
        """Make hash using HMAC"""

        # If no salt is give, which will be the case for signup,
        # create a salt
        if not salt:
            salt = cls.make_salt()
        h = hmac.new(salt, password).hexdigest()
        return "%s|%s" % (h, salt)

    @classmethod
    def valid_pw(cls, password, h):
        """Check if the given password hash is valid"""
        salt = str(h.split('|')[-1])
        return h == cls.make_hash(password, salt)

    @classmethod
    def valid_id(cls, id_hash):
        """Check id hash from 'username' cookie"""
        key_id = id_hash.split('|')[0]
        created_id_hash = cls.make_hash(key_id, SECRET).split('|')[0]
        if created_id_hash == id_hash.split('|')[-1]:
            return id_hash


class Wiki(db.Model):
    url = db.StringProperty(required=True)
    content = db.ListProperty(db.Text)
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.ListProperty(datetime.datetime)

    @classmethod
    def checkWiki(cls, page_url):
        """Check if a page with given url exist"""
        page = Wiki.all().filter('url = ', page_url).get()
        if page:
            return page
        else:
            return False
