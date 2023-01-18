from datetime import datetime
from flaskblog import db, login_manager,app
from flask_login import UserMixin
from itsdangerous import Serializer
from sqlalchemy.orm import relationship


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)    


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post',lazy=True)
    followed = db.relationship('Follow', foreign_keys=[Follow.follower_id],backref=db.backref('follower', lazy='joined'), lazy='dynamic',cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id],backref=db.backref('followed', lazy='joined'), lazy='dynamic',cascade='all, delete-orphan')
    num_followers = db.Column(db.Integer, default=0)
    num_following = db.Column(db.Integer, default=0)
    created_posts = db.relationship('Post', backref='author', lazy=True,overlaps='posts')
    

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(Follow(followed=user))

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            self.followed.remove(f)

    def is_following(self, user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    def get_reset_token(self,expires_sec='1800'):
        s= Serializer(app.config['SECRET_KEY'],expires_sec)
        return s.dumps({'user_id': self.id})


    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.email}', '{self.password}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    likes = db.Column(db.Integer, default=0, nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)
    user = db.relationship('User', lazy=True)


    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}','{self.image_file}')"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user = db.relationship('User', backref='comments')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)        