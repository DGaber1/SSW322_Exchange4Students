from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus_share.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_per_day = db.Column(db.Float, nullable=False)
    security_deposit = db.Column(db.Float, nullable=False, default=0.0)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref='items', foreign_keys=[owner_id])

class RentalTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime)
    deposit_paid = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item = db.relationship('Item', backref='rentals')
    borrower = db.relationship('User', backref='rentals', foreign_keys=[borrower_id])

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    user = db.relationship('User', backref='reviews', foreign_keys=[user_id])
    item = db.relationship('Item', backref='reviews')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    recent_items = Item.query.filter_by(is_available=True).order_by(Item.created_at.desc()).limit(6).all()
    return render_template('index.html', recent_items=recent_items)

@app.route('/browse')
def browse():
    category = request.args.get('category', '')
    search_query = request.args.get('search', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    query = Item.query.filter_by(is_available=True)
    
    if category:
        query = query.filter_by(category=category)
    if search_query:
        query = query.filter(Item.title.contains(search_query) | Item.description.contains(search_query))
    if min_price:
        query = query.filter(Item.price_per_day >= min_price)
    if max_price:
        query = query.filter(Item.price_per_day <= max_price)
    
    items = query.order_by(Item.created_at.desc()).all()
    categories = ['electronics', 'books', 'furniture', 'clothing', 'sports', 'other']
    
    return render_template('browse.html', items=items, categories=categories)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    reviews = Review.query.filter_by(item_id=item_id).all()
    
    # Calculate average rating
    from sqlalchemy import func
    avg_rating = db.session.query(func.avg(Review.rating)).filter_by(item_id=item_id).scalar() or 0
    
    return render_template('item_detail.html', item=item, reviews=reviews, avg_rating=avg_rating)

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post_item():
    if request.method == 'POST':
        item = Item(
            title=request.form['title'],
            description=request.form['description'],
            price_per_day=float(request.form['price_per_day']),
            security_deposit=float(request.form['security_deposit']),
            category=request.form['category'],
            location=request.form['location'],
            condition=request.form['condition'],
            owner_id=current_user.id
        )
        db.session.add(item)
        db.session.commit()
        flash('Item posted successfully!', 'success')
        return redirect(url_for('my_listings'))
    
    return render_template('post_item.html')

@app.route('/my-listings')
@login_required
def my_listings():
    items = Item.query.filter_by(owner_id=current_user.id).all()
    return render_template('my_listings.html', items=items)

@app.route('/rent/<int:item_id>', methods=['POST'])
@login_required
def rent_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    if item.owner_id == current_user.id:
        flash('You cannot rent your own item!', 'danger')
        return redirect(url_for('item_detail', item_id=item_id))
    
    if not item.is_available:
        flash('This item is no longer available!', 'danger')
        return redirect(url_for('item_detail', item_id=item_id))
    
    rental = RentalTransaction(
        item_id=item_id,
        borrower_id=current_user.id,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7),
        deposit_paid=item.security_deposit
    )
    
    item.is_available = False
    db.session.add(rental)
    db.session.commit()
    
    flash('Item rented successfully! Please coordinate with the owner for pickup.', 'success')
    return redirect(url_for('my_rentals'))

@app.route('/my-rentals')
@login_required
def my_rentals():
    rentals = RentalTransaction.query.filter_by(borrower_id=current_user.id).all()
    return render_template('my_rentals.html', rentals=rentals)

@app.route('/return-item/<int:rental_id>', methods=['POST'])
@login_required
def return_item(rental_id):
    rental = RentalTransaction.query.get_or_404(rental_id)
    
    if rental.borrower_id != current_user.id:
        flash('Unauthorized action!', 'danger')
        return redirect(url_for('my_rentals'))
    
    rental.return_date = datetime.now()
    rental.status = 'returned'
    
    item = Item.query.get(rental.item_id)
    item.is_available = True
    
    db.session.commit()
    flash('Item marked as returned. Security deposit will be processed within 24 hours.', 'success')
    return redirect(url_for('my_rentals'))

@app.route('/review/<int:item_id>', methods=['GET', 'POST'])
@login_required
def leave_review(item_id):
    if request.method == 'POST':
        review = Review(
            rating=int(request.form['rating']),
            comment=request.form['comment'],
            user_id=current_user.id,
            item_id=item_id
        )
        db.session.add(review)
        db.session.commit()
        
        # Update item owner's rating
        item = Item.query.get(item_id)
        from sqlalchemy import func
        avg_rating = db.session.query(func.avg(Review.rating)).filter_by(item_id=item_id).scalar()
        if avg_rating:
            item.owner.rating = float(avg_rating)
            db.session.commit()
        
        flash('Review submitted successfully!', 'success')
        return redirect(url_for('item_detail', item_id=item_id))
    
    item = Item.query.get_or_404(item_id)
    return render_template('leave_review.html', item=item)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Check if user exists
        if User.query.filter_by(email=request.form['email']).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username already taken!', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password_hash=generate_password_hash(request.form['password']),
            is_verified=False
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# Create tables and sample data
with app.app_context():
    db.create_all()
    
    # Create sample data if empty
    if User.query.count() == 0:
        print("Creating sample data...")
        # Create sample users
        user1 = User(username='alex_chen', email='alex@campus.edu', 
                     password_hash=generate_password_hash('password123'), is_verified=True, rating=4.5)
        user2 = User(username='jasmine_wong', email='jasmine@campus.edu', 
                     password_hash=generate_password_hash('password123'), is_verified=True, rating=4.8)
        
        db.session.add_all([user1, user2])
        db.session.commit()
        
        # Create sample items
        item1 = Item(title='MacBook Pro 14-inch', 
                     description='Great condition, perfect for coding. Comes with charger and case.',
                     price_per_day=25, security_deposit=200, category='electronics',
                     location='Library Quad', condition='like_new', owner_id=user1.id)
        item2 = Item(title='Calculus Textbook',
                     description='Essential textbook for Calculus I, II, and III. Lightly used.',
                     price_per_day=5, security_deposit=40, category='books',
                     location='Science Building', condition='good', owner_id=user2.id)
        item3 = Item(title='DSLR Camera Kit',
                     description='Canon EOS Rebel T7i with lens. Perfect for photography class.',
                     price_per_day=35, security_deposit=300, category='electronics',
                     location='Arts Center', condition='good', owner_id=user1.id)
        
        db.session.add_all([item1, item2, item3])
        db.session.commit()
        print("Sample data created!")

if __name__ == '__main__':
    app.run(debug=True)