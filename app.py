from flask import Flask, request, jsonify 
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask_marshmallow import Marshmallow
from datetime import date
from typing import List
from  marshmallow import ValidationError, fields
from sqlalchemy import select, delete

app = Flask(__name__) # creating instance of flask class

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:your_password@localhost/ecom'
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class= Base)
ma = Marshmallow(app)

class Customer(Base):
    __tablename__ = "customer"

    # Mapping class attributes to table columns
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(db.String(75), nullable=False)
    user_name : Mapped[str] = mapped_column(db.String(75),nullable=False)
    password : Mapped[str] = mapped_column(db.String(50), nullable=False)
    email : Mapped[str] = mapped_column(db.String(150))
    phone : Mapped[str] = mapped_column(db.String(16))
   
    # Create a one-many relationship to Orders table
    orders : Mapped[List["Orders"]] = db.relationship(back_populates="customer") 


order_products = db.Table (
    "order_products",
    Base.metadata,
    db.Column("order_id", db.ForeignKey('orders.id'),primary_key = True),
    db.Column("product_id",db.ForeignKey('products.id'),primary_key=True)
)

class Orders(Base):
    __tablename__ = "orders"

    id : Mapped[int] = mapped_column(primary_key=True)
    order_date : Mapped[date] = mapped_column(db.Date, nullable=False)
    customer_id : Mapped[int] = mapped_column(db.ForeignKey("customer.id")) 

    # Many to One rel to the customer table
    customer: Mapped['Customer'] = db.relationship(back_populates="orders")
    # Create many-many rel to Products through association table order_products
    products: Mapped[List['Products']] = db.relationship(secondary=order_products)


class Products(Base):
    __tablename__ = "products"

    id : Mapped[int] = mapped_column(primary_key=True)
    product_name : Mapped[str] = mapped_column(db.String(30), nullable=False)
    price : Mapped[float] = mapped_column(db.Float, nullable=False)

   
with app.app_context():
    # db.drop_all() 
    db.create_all() 

#========== Creating endpoints & schema to validate data ==========#

# Validate Customer data

class CustomerSchema (ma.Schema):
    id = fields.Integer(required=False)
    name = fields.String(required=True)
    username = fields.String(required=True)
    password = fields.String(required=True)
    email = fields.String(required=False)
    phone = fields.String(required=False)

    class Meta:
        fields = ('id','name','user_name','password','email','phone')



class OrdersSchema(ma.Schema):
    id = fields.Integer(required=False)
    order_date = fields.Date(required=False)
    customer_id = fields.Integer(required=True)

    class Meta:
        fields = ('id','order_date','customer_id','items')  # Items is list of product id for the 'order'


class ProductsSchema(ma.Schema):
    id = fields.Integer(required=False)
    product_name = fields.String(required=True)
    price = fields.Float(required=True)

    class Meta:
        fields = ('id','product_name','price')


customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

order_schema = OrdersSchema()
orders_schema = OrdersSchema(many=True)

product_schema = ProductsSchema()
products_schema = ProductsSchema(many=True)



@app.route('/')
def home():
    return "🌍E-commerce🛒"


#======== CRUD OPPS ========#
#============ GET REQUEST ============#

# GET CUSTOMERS
@app.route("/customers", methods = ["GET"])
def get_customers():
    query = select(Customer) # SELECT * FROM CUSTOMER
    result = db.session.execute(query).scalars() 
    customers = result.all()
    return customers_schema.jsonify(customers)


# GET PRODUCTS
@app.route("/products", methods = ["GET"])
def get_products():
    query = select(Products)
    result = db.session.execute(query).scalars()
    products = result

    return products_schema.jsonify(products)



# GET SPECIFIC CUSTOMER
@app.route("/customers/<int:id>", methods = ["GET"])
def get_customer_info(id):
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalar()
    
    if result is None:
        return jsonify({"Error": "Customer not found"}),404
    
    return customer_schema.jsonify(result)


# GET SPECIFIC ORDER_ITEMS
@app.route("/order_items/<int:id>", methods = ["GET"])
def get_order_items(id):
    query = select(Orders).where(Orders.id == id)
    order = db.session.execute(query).scalar()

    return products_schema.jsonify(order.products)


# GET SPECIFIC PRODUCT
@app.route("/products/<int:id>", methods = ["GET"])
def get_product_info(id):
    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalar()

    if result is None:
        return jsonify({"Message": "Product not found"})
    
    return product_schema.jsonify(result)


#============ POST REQUEST ============#

# CREATE PRODUCT W. POST request
@app.route("/products", methods = ["POST"])
def add_product():
    try: 
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages),400

    new_product = Products(product_name = product_data["product_name"], price = product_data["price"])

    db.session.add(new_product)
    db.session.commit()

    return jsonify({"Message": "New Product created"}),201


# CREATE CUSTOMER W. POST request
@app.route("/customers", methods = ["POST"])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages),400

    new_customer = Customer(name = customer_data['name'],user_name = customer_data['user_name'],password = customer_data['password'], email = customer_data['email'], phone = customer_data['phone'])

    db.session.add(new_customer)
    db.session.commit()

    return jsonify({"Message":"New customer added successfully"}),201


# CREATE ORDER W. POST request
@app.route("/orders", methods = ["POST"])
def create_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages),400
    
    new_order = Orders(order_date = date.today(), customer_id= order_data["customer_id"])

    for item_id in order_data["items"]:
        query = select(Products).where(Products.id == item_id)
        item = db.session.execute(query).scalar()

        new_order.products.append(item)
    
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"Message": "New Order Placed!"}),201


#============ PUT REQUEST ============#

# UPDATE CUSTOMER W. PUT request
@app.route("/customers/<int:id>", methods = ["PUT"])
def update_customer(id):
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalar()

    if result is None:
        return jsonify({"Error":"Customer not found"}),404

    customer = result

    # validate data
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages),400

    for field, value in customer_data.items():
        setattr(customer,field,value)

    db.session.commit()
    return jsonify({"Message": "Customer details updated"})


# UPDATE PRODUCTS W. PUT request
@app.route("/products/<int:id>", methods = ["PUT"])
def update_products(id):
    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalar()

    if result is None:
        return jsonify({"Error":"Product not found"}),404

    product = result

    # validate data
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages),400

    for field, value in product_data.items():
        setattr(product,field,value)

    db.session.commit()
    return jsonify({"Message": "Product details updated"})


#============ DELETE REQUEST ============#

# DELETE CUSTOMER W. DELETE request
@app.route("/customers/<int:id>", methods = ["DELETE"])
def delete_customer(id):
    query = delete(Customer).where(Customer.id == id)
    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({"Error":"Customer not found"})

    db.session.commit()
    return jsonify({"Messages":"Customer successfully deleted"}),200
    

# DELETE PRODUCT W. DELETE request
@app.route("/products/<int:id>", methods = ["DELETE"])
def delete_product(id):
    query = delete(Products).where(Products.id == id)
    result = db.session.execute(query)
    
    if result.rowcount == 0:
        return jsonify({"Error":"Product not found"})

    db.session.commit()
    return jsonify({"Messages":"Product successfully deleted"}),200
    

if __name__ == "__main__":
    app.run(debug = True)


