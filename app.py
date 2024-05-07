from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Flask_friends.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

followers = db.Table('followers',
                     db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
                     db.Column('followed_id', db.Integer, db.ForeignKey('user.id')))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/posts')
@login_required
def posts():
    posts_page = Post.query.order_by(Post.id.desc()).all()
    return render_template('posts.html', posts=posts_page)


@app.route('/')
@login_required
def index():
    users = User.query.order_by(User.id.desc()).all()
    return render_template('index.html', users=users)


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = current_user.id

        post = Post(title=title, content=content, user_id=user_id)
        db.session.add(post)
        db.session.commit()

        flash('Запись успешно создана!', 'success')
        return redirect(url_for('posts'))

    return render_template('new_post.html')


@app.route('/post/delete/<int:del_id>')
@login_required
def delete_post(del_id):
    post_to_delete = Post.query.get_or_404(del_id)

    try:
        db.session.delete(post_to_delete)
        db.session.commit()
        flash('Запись успешно удалена!', 'success')

        my_posts = current_user.posts
        return render_template('user_page.html', my_posts=my_posts)

    except:
        flash('Запись не удалена!', 'success')

        my_posts = current_user.posts
        return render_template('user_page.html', my_posts=my_posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('You have been registered successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('user_page'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/user')
@login_required
def user_page():
    my_posts = current_user.posts
    return render_template('user_page.html', my_posts=my_posts)


@app.route('/friends')
@login_required
def friends():
    user_now = current_user.id
    friend = User.query.join(
        followers, (followers.c.followed_id == User.id)).filter(
        followers.c.follower_id == user_now).all()
    return render_template('friends.html', friend=friend)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Пользователя {} не существует.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('Ты не можешь добавить себя')
        return redirect(url_for('index', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('{} добавлен в друзья!'.format(username))
    return redirect(url_for('user_page', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('new_user', username=username))


if __name__ == '__main__':
    app.run(debug=True)
