""" Request handlers used in main.py of andrea-shinnigan"""

import datetime
import jinja2
import model
import os
import time
import webapp2

from google.appengine.ext import db

# path to html files
template_dir = os.path.join(os.path.dirname(__file__), 'html')
# jinja environment to html files
jinja_env = jinja2.Environment(autoescape=True,
                               loader=jinja2.FileSystemLoader(template_dir))

# Save oftenly used classes to local variables
Account = model.Account
Wiki = model.Wiki


class Handler(webapp2.RequestHandler):
    login = None  # Store login status

    def __init__(self, request, response):
        self.initialize(request, response)

        self.login = self.read_login_cookie()  # Always check login status

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def _render_str(self, template, **kw):
        """Use jinja to render string"""
        t = jinja_env.get_template(template)
        return t.render(**kw)

    def render(self, template, **kw):
        """Render an html file. Depending on login status, rendering might
        change slightly."""
        if self.login:
            self.write(self._render_str(template, login=True, **kw))
        else:
            self.write(self._render_str(template, login=False, **kw))

    def set_login_cookie(self, key_id):
        """Set a login cookie"""
        id_hash = Account.make_hash(key_id, model.SECRET).split('|')[0]
        content = 'user=%s|%s; Path=/' % (key_id, id_hash)
        self.response.headers.add_header('Set-Cookie', content)

    def read_login_cookie(self):
        """Read login cookie and check its validity"""
        cookie_val = self.request.cookies.get('user')
        if cookie_val:
            return cookie_val and Account.valid_id(cookie_val)
        else:
            return False


class SignupHandler(Handler):
    def signup_render(self, **kw):
        self.render('signup.html', **kw)

    def get(self):
        self.signup_render(initial=True)

    def post(self):
        error_bool = False
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")

        # Save all the parameters that might be passed onto signup_render
        # into a dictionary
        params = dict(username=username,
                      password=password,
                      email=email)

        # Verify all the signup parameters
        error_params = Account.signup_verify(username=username,
                                             password=password,
                                             verify=verify,
                                             email=email)

        # Create error message for each error flags
        if not error_params["username_flag"]:
            params['error_username'] = "Invalid user name."
            error_bool = True

        if not error_params["password_flag"]:
            params['error_password'] = "Invalid password."
            error_bool = True

        if not error_params["verify_flag"]:
            params['error_verify'] = "Does not match with the password."
            error_bool = True

        if not error_params["email_flag"]:
            params["error_email"] = "Invalid email."
            error_bool = True

        if error_params["account_flag"]:
            params["error_account"] = "This user name already exists."
            error_bool = True

        if error_bool:
            # If there is any error, rerender signup.html with error messages
            self.signup_render(**params)
        else:
            # If there is no error, create an account
            pw_hash = Account.make_hash(password)
            a = Account(username=username, password=pw_hash)
            if email:
                a.email = email
            a_key_id = str(a.put().id())  # account id
            self.set_login_cookie(a_key_id)  # create login cookie

            self.redirect('/welcome')  # redirect to welcome page


class WelcomeHandler(Handler):
    def get(self):
        if self.login:  # only render welcome.html if logged in
            account = Account.get_by_id(int(self.login.split('|')[0]))
            self.render('welcome.html', username=account.username)
        else:
            self.redirect('/signup')


class LoginHandler(Handler):
    def login_render(self, **kw):
        self.render('login.html', **kw)

    def get(self):
        self.login_render(initial=True)

    def post(self):
        error_bool = False
        username = self.request.get("username")
        password = self.request.get("password")

        # Save all the parameters that might be passed onto login_render
        # into a dictionary
        params = dict(username=username)

        # Check if an account with the given username exists
        account = Account.check_account(username)
        if not account:
            params['error_username'] = "This user does not exist."
            error_bool = True
        else:
            pw_hash = account.password

            # Check for the validity of the given password
            if not Account.valid_pw(password, pw_hash):
                params['error_password'] = "Incorrect password"
                error_bool = True

        if error_bool:
            # If there is any error, rerender login.html with error messages
            self.login_render(**params)
        else:
            a_key_id = str(account.key().id())
            self.set_login_cookie(a_key_id)  # Create login cookie

            self.redirect('/')


class LogoutHandler(Handler):
    def get(self):
        """Logouts a user by deleting the 'user' cookie"""
        self.response.headers.add_header('Set-Cookie', 'user=; Path=/')
        self.redirect('/')


class EditHandler(Handler):
    page = None

    def edit_render(self):
        if self.page:
            # if a page exist, render the last content with edit.html
            self.render('edit.html', content=self.page.content[-1])
        else:
            self.render('edit.html')

    def get(self, page_url):
        if self.login:  # only allowed to edit when logged in
            # check for a page with given url
            self.page = Wiki.checkWiki(page_url)
            self.edit_render()
        else:
            self.render('wiki.html', error_edit=True)

    def post(self, page_url):
        self.page = Wiki.checkWiki(page_url)
        content = self.request.get('content')
        if self.page:  # if page already exists, only append to existing data
            self.page.content.append(db.Text(content))
            self.page.modified.append(datetime.datetime.now())
        else:  # create a new entry for a new page
            self.page = Wiki(content=[db.Text(content)],
                             url=page_url, modified=[datetime.datetime.now()])

        self.page.put()  # commit the change
        time.sleep(0.1)  # give enough time for database to update

        self.redirect(page_url)


class WikiHandler(Handler):
    def get(self, page_url):
        # check for a page with given url
        page = Wiki.checkWiki(page_url)
        if page:  # render wiki page if the page exist
            # if version number is given, render the corresponding version
            index = self.request.get("v")
            if not index:
                index = -1
            else:
                index = int(index)
            self.render('wiki.html', url=page_url, content=page.content[index])
        elif self.login:  # if page does not exist, but logged in, allow edit
            self.redirect('/_edit' + page_url)
        else:  # if page does not exist and not logged in, give 404 message
            self.render('wiki.html', error_wiki=True)


class HistoryHandler(Handler):
    def get(self, page_url):
        if self.login:  # only allowed to view page history when logged in
            page = Wiki.checkWiki(page_url)
            self.render('history.html', page=page, url=page_url)
        else:
            self.render('wiki.html', error_history=True)
