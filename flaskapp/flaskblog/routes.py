import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, EmptyForm, RequestResetForm , ResetPasswordForm, SearchForm, ConfirmationForm,CommentForm,LikeForm
from flaskblog.models import User, Post,Like,Comment,Follow
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Mail,Message
from sqlalchemy import desc

import smtplib



@app.route("/")
@app.route("/home")
@login_required
def home():
    followed_users = db.session.query(Follow).filter_by(follower_id=current_user.id).join(Follow.followed).all()
    followed_user_ids = [user.followed_id for user in followed_users]
    post_query = Post.query.join(Post.user).filter(User.id.in_(followed_user_ids)).order_by(Post.date_posted.desc())
    page = request.args.get('page', 1, type=int)
    posts = post_query.paginate(page=page, per_page=20)
    return render_template('home.html', posts=posts)


@app.route("/about")
@login_required
def about():
    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(desc(Post.date_posted)).all()
    return render_template('about.html',user_posts=user_posts,title='My Posts ')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        print("Form data:", form.data)
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('You have been logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form, user=current_user)

def save_post_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/post_images', picture_fn)
    form_picture = Image.open(picture_path)
    form_picture.save(picture_path)
    return picture_fn


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        
        if form.picture.data:
            picture_file = save_post_picture(form.picture.data)
            post.image_file = picture_file
            db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('about'))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post')


 
@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('home'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user_profile', username=username))
        if current_user.is_following(user):
            flash('You are already following {}!'.format(username))
            return redirect(url_for('user_profile', username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('user_profile', username=username))
    else:
        return redirect(url_for('home'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('home'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user_profile', username=username))
        if not current_user.is_following(user):
            flash('You are not following {}!'.format(username))
            return redirect(url_for('user_profile', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {}.'.format(username))
        return redirect(url_for('user_profile', username=username))
    else:
        return



@app.route("/post/<int:post_id>")
def post(post_id):
    form=PostForm()
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post,form=form)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('user_profile.html')

@app.route('/search', methods=['GET','POST'])
def search():
    form = SearchForm()
    if request.method == 'POST' and form.validate_on_submit():
        return redirect((url_for('search_results', query=form.search.data)))
    return render_template('search.html',form=form)


@app.route('/search-results', methods=['GET'])
def search_results():
    username = request.args.get('username')
    results = User.query.filter(User.username.like(f'%{username}%')).all()
    return render_template('search_results.html', results=results)


@app.route('/user/<string:username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    all_posts = Post.query.all()
    blog_count = len(all_posts)
    form=EmptyForm()
    return render_template('user_profile.html', user=user,form=form,posts=all_posts,blog_count=blog_count)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='padmaja121003@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    with smtplib.SMTP('smtp.sendgrid.net', 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login('apikey', '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')
        smtp.send_message(msg)





@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route('/user/<string:username>/blogs')
def user_blogs(username):
    user = User.query.filter_by(username=username).first_or_404()
    blog_count = len(user.posts)
    return render_template('user_blogs.html', user=user, blog_count=blog_count)


@app.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    form = ConfirmationForm()
    if form.validate_on_submit():
        if form.confirm.data:
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
            flash('Your account has been deleted.', 'success')
            return redirect(url_for('home'))
    return render_template('delete_account.html', form=form)

@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    form=LikeForm()
    post = Post.query.get(post_id)
    user_liked = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if user_liked:
        flash('You have already liked this post', 'danger')
    like = Like(user_id=current_user.id, post_id=post.id)
    db.session.add(like)
    db.session.commit()
    return redirect(url_for('post', post_id=post.id,form=form))


@app.route('/post/<int:post_id>/comment', methods=['GET', 'POST'])
@login_required
def comment_post(post_id):
    form = CommentForm()
    post = Post.query.get(post_id)
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, user_id=current_user.id, post_id=post.id)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('post', post_id=post.id))
    return render_template('comment.html', form=form, post=post)

