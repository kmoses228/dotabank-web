from flask import Blueprint, render_template, flash, redirect, request, url_for, current_app

from app import oid, steam, db, login_manager
from models import User, AnonymousUser
from forms import SettingsForm
from flask.ext.login import login_user, logout_user, current_user, login_required
from app.admin.views import AdminModelView
from app.replays.models import ReplayFavourite, ReplayRating, ReplayDownload, ReplayPlayer, Replay, Search

mod = Blueprint("users", __name__, url_prefix="/users")

login_manager.anonymous_user = AnonymousUser


# User authentication
@login_manager.user_loader
def load_user(user_id):
    _user = User.query.get(user_id)
    if _user:
        _user.update_last_seen()
    return _user


@mod.route('/login/')
@oid.loginhandler
def login():
    if current_user.is_authenticated():
        return redirect(oid.get_next_url())
    return oid.try_login('http://steamcommunity.com/openid')


@oid.after_login
def create_or_login(resp):
    steam_id = long(resp.identity_url.replace("http://steamcommunity.com/openid/id/", ""))
    account_id = int(steam_id & 0xFFFFFFFF)
    _user = User.query.filter(User.id == int(account_id & 0xFFFFFFFF)).first()

    if not _user:
        _user = User(int(account_id & 0xFFFFFFFF), steam.user.profile(steam_id).persona or account_id)

        db.session.add(_user)
        db.session.commit()

    login_attempt = login_user(_user)
    if login_attempt is True:
        flash("You are logged in as {}".format(_user.name), "success")
    elif not _user.is_active():
        flash("Cannot log you in as {}, your account has been disabled.  If you believe this is in error, please contact {}.".format(_user.name, current_app.config["CONTACT_EMAIL"]), "danger")
    else:
        flash("Error logging you in as {}, please try again later.".format(_user.name), "danger")
    return redirect(oid.get_next_url())


@mod.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(oid.get_next_url())


@mod.route("/")
@mod.route("/page/<int:page>/")
def users(page=1):
    if not current_user.is_admin():
        flash("User list is admin only atm.", "danger")
        return redirect(request.referrer or url_for("index"))
    _users = User.query.paginate(page, current_app.config["USERS_PER_PAGE"], False)
    return render_template("users/users.html", users=_users)


@mod.route("/<int:_id>/")
def user(_id):
    _user = User.query.filter(User.id == _id).first()

    if _user is None:
        flash("User {} not found.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))

    favourites = ReplayFavourite.query.\
        filter(ReplayFavourite.user_id == _user.id).\
        order_by(ReplayFavourite.created_at.desc()).\
        limit(current_app.config["LATEST_REPLAYS_LIMIT"]).\
        all()

    ratings = ReplayRating.query.\
        filter(ReplayRating.user_id == _user.id).\
        order_by(ReplayRating.created_at.desc()).\
        limit(current_app.config["LATEST_REPLAYS_LIMIT"]).\
        all()

    searches = Search.query.\
        filter(Search.user_id == _user.id).\
        order_by(Search.created_at.desc()).\
        limit(current_app.config["LATEST_REPLAYS_LIMIT"]).\
        all()

    downloads = ReplayDownload.query.\
        join(ReplayDownload.replay).\
        filter(ReplayDownload.user_id == _user.id).\
        order_by(ReplayDownload.created_at.desc()).\
        limit(current_app.config["LATEST_REPLAYS_LIMIT"]).\
        all()

    replays_participated = ReplayPlayer.query.\
        join(ReplayPlayer.replay).\
        filter(ReplayPlayer.account_id == _user.id).\
        order_by(Replay.start_time.desc()).\
        limit(current_app.config["LATEST_REPLAYS_LIMIT"]).\
        all()

    return render_template("users/user.html",
                           user=_user,
                           favourites=favourites,
                           ratings=ratings,
                           searches=searches,
                           downloads=downloads,
                           replays_participated=replays_participated)

@mod.route("/<int:_id>/replays/")
@mod.route("/<int:_id>/replays/<int:page>/")
def user_replays(_id, page=1):
    _user = User.query.filter(User.id == _id).first()
    if _user is None:
        flash("User {} not found.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))
    _replays = _user.replay_players.paginate(page, current_app.config["REPLAYS_PER_PAGE"], False)
    return render_template("users/replays.html", user=_user, replays=_replays)

@mod.route("/<int:_id>/favourites/")
@mod.route("/<int:_id>/favourites/<int:page>/")
def user_favourites(_id, page=1):
    _user = User.query.filter(User.id == _id).first()
    if _user is None:
        flash("User {} not found.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))
    _favourites = _user.favourites.paginate(page, current_app.config["REPLAYS_PER_PAGE"], False)
    return render_template("users/favourites.html", user=_user, favourites=_favourites)

@mod.route("/<int:_id>/ratings/")
@mod.route("/<int:_id>/ratings/<int:page>/")
def user_ratings(_id, page=1):
    _user = User.query.filter(User.id == _id).first()
    if _user is None:
        flash("User {} not found.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))
    _favourites = _user.replay_ratings.paginate(page, current_app.config["REPLAYS_PER_PAGE"], False)
    return render_template("users/ratings.html", user=_user, favourites=_favourites)

@mod.route("/<int:_id>/searches/")
@mod.route("/<int:_id>/searches/<int:page>/")
def user_searches(_id, page=1):
    _user = User.query.filter(User.id == _id).first()
    if _user is None:
        flash("User {} not found.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))
    _favourites = _user.searches.paginate(page, current_app.config["REPLAYS_PER_PAGE"], False)
    return render_template("users/searches.html", user=_user, favourites=_favourites)

@mod.route("/<int:_id>/downloads/")
@mod.route("/<int:_id>/downloads/<int:page>/")
def user_downloads(_id, page=1):
    _user = User.query.filter(User.id == _id).first()
    if _user is None:
        flash("User {} not found.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))
    _downloads = _user.downloads.paginate(page, current_app.config["REPLAYS_PER_PAGE"], False)
    return render_template("users/downloads.html", user=_user, downloads=_downloads)



@mod.route("/<int:_id>/settings/", methods=["POST", "GET"])
@login_required
def settings(_id):
    # Authentication
    if current_user.id != _id and not current_user.is_admin():
        flash("You are not authorised to edit user {}'s settings.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))

    # Check user exists
    _user = User.query.filter(User.id == _id).first()
    if _user is None:
        flash("User {} not found.".format(_id), "danger")
        return redirect(request.referrer or url_for("index"))

    # Validate form, if submitted; else render it.
    form = SettingsForm(_user, request.form)

    if form.validate_on_submit():
        _user.name = form.name.data
        _user.email = form.email.data
        _user.show_ads = form.show_ads.data
        db.session.add(_user)
        db.session.commit()
        return redirect(request.args.get("next") or url_for("index"))

    return render_template("users/settings.html", user=_user, form=form)


class UserAdmin(AdminModelView):
    column_display_pk = True

    def __init__(self, session, **kwargs):
        # Just call parent class with predefined model.
        super(UserAdmin, self).__init__(User, session, **kwargs)
