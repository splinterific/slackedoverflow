import os

# application import statements
from application import (
    actions_logic,
    app,
    db,
    forms,
    json_format,
    misc_func,
    models,
    Oauth_logic

)
from flask import (
    Flask,
    flash,
    json,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for
)

from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user
)


from werkzeug.urls import url_parse


from slackclient import SlackClient


import os

b_token = app.config['BOT_TOKEN']
u_token = app.config['USER_TOKEN']
veri = app.config['VERIFICATION_TOKEN']
oauth_scope = app.config['OAUTH_SCOPE']
client_id = app.config['CLIENT_ID']
client_secret = app.config['CLIENT_SECRET']


# Global reference for the Slack Client tokens
sc = SlackClient(b_token)
sc_user = SlackClient(u_token)


# Main index page
@app.route("/index")
@app.route("/")
@login_required
def index():

    return render_template('index.html')


# login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = forms.LoginForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
            flash("You've been logged in")
        return redirect(next_page)

    return render_template('login.html', form=form)


@app.route("/posts_page", methods=["GET", "POST"])
@login_required
def posts_page():
    form = forms.SearchBar()

    # if current_user.is_authenticated:
    #     return render_template("posts.html", posts=posts, form=form)
    if form.validate_on_submit():
        posts = models.Post.query.all()
        posts = models.Post.query
        posts = posts.filter(models.Post.message_text.like(
            '%' + form.searchterm.data + '%'))
        return render_template("post_results.html", posts=posts, form=form)
    else:
        posts = models.Post.query.all()

        return render_template("posts.html", posts=posts, form=form)

# logout page


@app.route('/logout')
def logout():
    logout_user()
    flash('Please login to continue')
    return redirect(url_for('login'))

# this returns to both the browser and also to slack


@app.route('/register', methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = forms.RegistrationForm()
    if form.validate_on_submit():
        user = models.User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations! you are now registered!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route("/ping", methods=["GET", "POST"])
def ping_slackside_endpoint():
    if request.method == "POST":
        misc_func.ping()
        return make_response("pong",
                             200
                             )
    else:
        return "pong"


# endpoint to be hit whenever a user action takes place in slack
@app.route("/actions", methods=["POST"])
def actions():
    payload = json.loads(request.form.get("payload"))
    if payload["token"] == veri:
        # debug checking of payload token
        # print("payload token ok")
        if payload["callback_id"] == "threadDis":
            # Uncomment to check the payload token is valid
            # print("payload callback ok")
            ts = payload["message"]["ts"]
            team_id = payload["team"]["id"]
            team_domain = payload["team"]["domain"]
            channel_id = payload["channel"]["id"]
            user_id = payload["user"]["id"]
            misc_func.post_write(team_id,
                                 team_domain, user_id, channel_id, ts)
            return make_response("OK", 200)
        else:
            return make_response("wrong token, who dis", 403)

    # actions_logic.action_calling(payload)

# This section and routes below looks after the oauth endpoints.
# These are used to control
# installing this app to Slack
# but is only needed while installing
# to a new team


# Oauth install endpoint
@app.route("/oauth_install", methods=["GET"])
def pre_install():
    return render_template("install_so.html",
                           oauth_scope=oauth_scope,
                           client_id=client_id
                           )


# Oauth finished endpoint
@app.route("/oauth_completed", methods=["GET", "POST"])
def post_install():
    auth_response = Oauth_logic.oauth_access()
    return f"Authed and installed to your team - {auth_response['team_name']}"
