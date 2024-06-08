from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json, os, math, bcrypt
from flask_mail import Mail

from werkzeug.utils import secure_filename
with open('config.json', 'r') as c:
    params = json.load(c)["params"]


local_server = True
app = Flask(__name__)
app.secret_key = 'asdfjkasdf-test'
# app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config['UPLOAD_FOLDER'] = './static/media'

@app.template_filter('truncate')
def truncate_filter(s, length=30):
    if len(s) <= length:
        return s
    return s[:length] + '...'

app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 465,
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail-user'],
    MAIL_PASSWORD=  params['gmail-password']
)
mail = Mail(app)

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __init__(self,username, email, password):
        self.username = username
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(12))


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(), nullable=True)
    content = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(25), nullable=False)
    date = db.Column(db.String(12))

def logged_in(session):
    if 'username' in session:
        return True
    else:
        return False

@app.route("/")
def home():   
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['posts-limit']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['posts-limit']) : (page-1)+int(params['posts-limit']) + int(params['posts-limit'])]
    if (page==1):
        prev = '#'
        next = '/?page='+str(page+1)
    
    elif (page == last):
        prev = '/?page='+str(page-1)
        next = '#'
    
    else:
        prev = '/?page='+ str(page-1)
        next = '/?page='+ str(page+1)
    
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    print("-----------")
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")
        new_entry = Contacts(name=name, email=email, phone=phone, message=message, date=datetime.now())
        try:
            db.session.add(new_entry)
            db.session.commit()
            mail.send_message("Flask Blog Email", sender=email, recipients = [params['gmail-user']],
                            body=message + "\n" + phone)
            flash("Your Message has been Sent Successfully", 'success')
        except Exception as e:
            flash("Something Went Wrong", 'danger')
            return f"Something went wrong:: {e}"
    return render_template("contact.html")


@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    get_post = Posts.query.filter_by(slug=post_slug).first()
    post = get_post if get_post else None
    
    return render_template('post.html', post=post)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if logged_in(session=session):
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            posts = Posts.query.all()
            flash("Logged In Successfully", 'success')
            return render_template("dashboard.html", params=params, posts=posts)
        else:
            flash("Invalid username or password", 'danger')
            return redirect('/dashboard')
        
    return render_template("login.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        if password != password2:
            flash("Passwords do not match", 'danger')
            return redirect("/register")

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("User Registered Successfully", 'success')
        return redirect("/dashboard")

    return render_template('register.html')



@app.route("/delete-post/<int:sno>")
def delete_post(sno):
    if logged_in(session=session):
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        flash("Your post has been deleted", 'danger')
        return redirect('/dashboard')
    else:
        flash("Please Login first", 'danger')
        return redirect('/dashboard')
    
@app.route("/edit-post/<int:sno>", methods=['GET', 'POST'])
def edit_post(sno):
    if logged_in(session=session):
        post = Posts.query.filter_by(sno=sno).first()
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            post.title = title
            post.content = content
            db.session.commit()
            flash("Your Post has been updated", 'success')
        return render_template("edit_post.html", post=post)
    else:
        flash("Please Login first", 'warning')
        return redirect("/dashboard")


@app.route("/upload-post", methods=['POST'])
def add_new_blog():
    if logged_in(session=session):
        title = request.form.get('title')
        content = request.form.get('content')
        img = request.files['img']
        blog_image = None
        if img:
            img.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(img.filename)))
            img_path = f"{img.filename}"
            blog_image = img_path.replace(" ",'_')
            print(blog_image)
        
        post = Posts(title=title, content=content, image=blog_image, slug=title.replace(' ', '-'), date=datetime.now())
        db.session.add(post)
        db.session.commit()
        flash("Your new post has been uploaded", 'success')
    
    return redirect('/dashboard')


@app.route("/logout")
def logout():
    session.pop('username')
    flash("You're logged out successfully", 'warning')
    return redirect('/dashboard')


app.run(debug=True)