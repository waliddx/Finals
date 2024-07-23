"""
Flask application that integrate 
admin and client sides
"""
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename


def create_app():
    '''app & database configurations'''

    app= Flask(__name__)
    app.secret_key= os.getenv("DATABASE")
    UPLOAD_FOLDER= 'static/uploads'
    ALLOWED_EXTENSIONS= set(['jpeg', 'jpg', 'png', 'gif'])
    app.config['UPLOAD_FOLDER']= UPLOAD_FOLDER

    def getLoginDetails():
        '''This function retrieves the login details and checks about it'''

        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            if 'email' not in session:
                loggedIn= False
                firstName= ''
                noOfItems= 0
            else:
                loggedIn= True
                cur.execute("SELECT userId, firstName FROM users WHERE email= ?", (session['email'], ))
                userId, firstName= cur.fetchone()
                cur.execute("SELECT count(productId) FROM kart WHERE userId= ?", (userId, ))
                noOfItems= cur.fetchone()[0]
        conn.close()
        return (loggedIn, firstName, noOfItems)

    @app.route("/")
    def root():
        '''This function returns the main route'''

        loggedIn, firstName, noOfItems= getLoginDetails()
        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute('SELECT productId, name, price, description, image, stock FROM products')
            itemData= cur.fetchall()
            cur.execute('SELECT categoryId, name FROM categories')
            categoryData= cur.fetchall()
        itemData= parse(itemData)   
        return render_template('home.html', itemData=itemData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)

    @app.route("/add")
    def admin():
        '''This function returns the add items route'''

        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute("SELECT categoryId, name FROM categories")
            categories= cur.fetchall()
        conn.close()
        return render_template('items.html', categories=categories)


    @app.route("/addItem", methods=["GET", "POST"])
    def addItem():
        '''This function add the item data to the database'''

        if request.method == "POST":
            name= request.form['name']
            price= float(request.form['price'])
            description= request.form['description']
            stock= int(request.form['stock'])
            categoryId= int(request.form['category'])

            image= request.files['image']  # <- Uploading image procedure
            if image and allowed_file(image.filename):
                filename= secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagename= filename
            with sqlite3.connect('database.db') as conn:
                try:
                    cur= conn.cursor()
                    cur.execute('''INSERT INTO products (name, price, description, image, stock, categoryId) VALUES (?, ?, ?, ?, ?, ?)''', (name, price, description, imagename, stock, categoryId))
                    conn.commit()
                    msg="added successfully"
                except:
                    msg="error occured"
                    conn.rollback()
            conn.close()
            print(msg)
            return redirect(url_for('root'))


    @app.route("/remove")
    def remove():    
        '''This function returns the remove route'''

        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute('SELECT productId, name, price, description, image, stock FROM products')
            data= cur.fetchall()
        conn.close()
        return render_template('remove.html', data=data)


    @app.route("/removeItem")
    def removeItem():
        '''This function removes selected item from the database'''

        productId= request.args.get('productId')
        with sqlite3.connect('database.db') as conn:
            try:
                cur= conn.cursor()
                cur.execute('DELETE FROM products WHERE productID= ?', (productId, ))
                conn.commit()
                msg= "Deleted successsfully"
            except:
                conn.rollback()
                msg= "Error occured"
        conn.close()
        print(msg)
        return redirect(url_for('root'))


    @app.route("/displayCategory")
    def displayCategory():      
        '''This function return items found within thedatabase'''

        loggedIn, firstName, noOfItems= getLoginDetails()
        categoryId= request.args.get("categoryId")
        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute("SELECT products.productId, products.name, products.price, products.image, categories.name FROM products, categories WHERE products.categoryId= categories.categoryId AND categories.categoryId= ?", (categoryId, ))
            data= cur.fetchall()
        try:
            conn.close()
            categoryName= data[0][4]
            data= parse(data)
            return render_template('displayCategory.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)
        except:
            return render_template('displayCategory.html')


    @app.route("/account/profile")
    def profileHome():
        '''This function the profile route'''

        if 'email' not in session:
            return redirect(url_for('root'))
        loggedIn, firstName, noOfItems= getLoginDetails()
        return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

    @app.route("/account/profile/edit")
    def editProfile():
        '''This function returns the edit route'''
        if 'email' not in session:
            return redirect(url_for('root'))
        loggedIn, firstName, noOfItems= getLoginDetails()
        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute("SELECT userId, email, firstName, lastName, address1 FROM users WHERE email= ?", (session['email'], ))
            profileData= cur.fetchone()
        conn.close()
        return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

    @app.route("/updateProfile", methods=["GET", "POST"])
    def updateProfile():
        '''This function add the updated user data to the database'''

        if request.method == 'POST':
            firstName= request.form['firstName']
            lastName= request.form['lastName']
            address1= request.form['address1']
            with sqlite3.connect('database.db') as con:
                    try:
                        cur= con.cursor()
                        cur.execute('UPDATE users SET firstName= ?, lastName= ?, address1= ? WHERE email= ?', (firstName, lastName, address1))

                        con.commit()
                        msg= "Saved Successfully"
                    except:
                        con.rollback()
                        msg= "Error occured"
            con.close()
            return redirect(url_for('editProfile'))

    @app.route("/account/profile/changePassword", methods=["GET", "POST"])
    def changePassword():
        '''This function add the updated user password to the database'''

        if 'email' not in session:
            return redirect(url_for('loginForm'))
        if request.method == "POST":
            oldPassword= request.form['oldpassword']
            oldPassword= hashlib.md5(oldPassword.encode()).hexdigest()
            newPassword= request.form['newpassword']
            newPassword= hashlib.md5(newPassword.encode()).hexdigest()
            with sqlite3.connect('database.db') as conn:
                cur= conn.cursor()
                cur.execute("SELECT userId, password FROM users WHERE email= ?", (session['email'], ))
                userId, password= cur.fetchone()
                if (password == oldPassword):
                    try:
                        cur.execute("UPDATE users SET password= ? WHERE userId= ?", (newPassword, userId))
                        conn.commit()
                        msg="Changed successfully"
                    except:
                        conn.rollback()
                        msg= "Failed"
                    return render_template("changePassword.html", msg=msg)
                else:
                    msg= "Wrong password"
            conn.close()
            return render_template("changePassword.html", msg=msg)
        else:
            return render_template("changePassword.html")


    @app.route("/loginForm")
    def loginForm():
        '''This function returns a login route if user not connected '''

        if 'email' in session:
            return redirect(url_for('root'))
        else:
            return render_template('login.html', error='')

    @app.route("/login", methods= ['POST', 'GET'])
    def login():
        '''This function gets the user credentials and checks about it'''

        if request.method == 'POST':
            email= request.form['email']
            password= request.form['password']
            if is_valid(email, password):
                session['email']= email
                return redirect(url_for('root'))
            error= 'Invalid UserId / Password'
            return render_template('login.html', error=error)

    @app.route("/productDescription")
    def productDescription():
        '''This function returns the selected item's description'''

        loggedIn, firstName, noOfItems= getLoginDetails()
        productId= request.args.get('productId')
        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute('SELECT productId, name, price, description, image, stock FROM products WHERE productId= ?', (productId, ))
            productData= cur.fetchone()
        conn.close()
        return render_template("productDescription.html", data=productData, loggedIn= loggedIn, firstName= firstName, noOfItems= noOfItems)

    @app.route("/addToCart")
    def addToCart():
        '''This function add the selected item to the user is cart'''

        if 'email' not in session:
            return redirect(url_for('loginForm'))
        else:
            productId= int(request.args.get('productId'))
            with sqlite3.connect('database.db') as conn:
                cur= conn.cursor()
                cur.execute("SELECT userId FROM users WHERE email= ?", (session['email'], ))
                userId= cur.fetchone()[0]
                try:
                    cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
                    conn.commit()
                    msg= "Added successfully"
                except:
                    conn.rollback()
                    msg= "Error occured"
            conn.close()
            return redirect(url_for('root'))

    @app.route("/cart")
    def cart():
        '''This function returns the cart route is user is connected '''

        if 'email' not in session:
            return redirect(url_for('loginForm'))
        loggedIn, firstName, noOfItems= getLoginDetails()
        email= session['email']
        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute("SELECT userId FROM users WHERE email= ?", (email, ))
            userId= cur.fetchone()[0]
            cur.execute("SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId= kart.productId AND kart.userId= ?", (userId, ))
            products= cur.fetchall()
        totalPrice= 0
        for row in products:
            totalPrice += row[2]
        return render_template("cart.html", products= products, totalPrice= totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

    @app.route("/removeFromCart")
    def removeFromCart():
        '''This function removes the selected item from the cart'''

        if 'email' not in session:
            return redirect(url_for('loginForm'))
        email= session['email']
        productId= int(request.args.get('productId'))
        with sqlite3.connect('database.db') as conn:
            cur= conn.cursor()
            cur.execute("SELECT userId FROM users WHERE email= ?", (email, ))
            userId= cur.fetchone()[0]
            try:
                cur.execute("DELETE FROM kart WHERE userId= ? AND productId= ?", (userId, productId))
                conn.commit()
                msg= "removed successfully"
            except:
                conn.rollback()
                msg= "error occured"
        conn.close()
        return redirect(url_for('root'))

    @app.route("/logout")
    def logout():
        '''This function logout the user from the session'''

        session.pop('email', None)
        return redirect(url_for('root'))


    @app.route("/register", methods= ['GET', 'POST'])
    def register():
        '''This function add a new user's credentials to the database'''

        if request.method == 'POST':
            password= request.form['password']
            email= request.form['email']
            firstName= request.form['firstName']
            lastName= request.form['lastName']
            address1= request.form['address1']

            with sqlite3.connect('database.db') as con:
                try:
                    cur= con.cursor()
                    cur.execute('INSERT INTO users (password, email, firstName, lastName, address1) VALUES (?, ?, ?, ?, ?)', (hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1))

                    con.commit()

                    msg= "Registered Successfully"
                except:
                    con.rollback()
                    msg= "Error occured"
            con.close()
            return render_template("login.html", error=msg)

    @app.route("/registrationForm")
    def registrationForm():
        '''This function return the registration route'''

        return render_template("register.html")

    def is_valid(email, password):
        '''This function checks about the user's credentials in the database'''
        con= sqlite3.connect('database.db')
        cur= con.cursor()
        cur.execute('SELECT email, password FROM users')
        data= cur.fetchall()
        for row in data:
            if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
                return True
        return False

    def allowed_file(filename):
        '''This function checks about the allowed images extensions'''

        return '.' in filename and \
                filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

    def parse(data):
        '''This function parse databse data'''

        ans= []
        i= 0
        while i < len(data):
            curr= []
            for j in range(7):
                if i >= len(data):
                    break
                curr.append(data[i])
                i += 1
            ans.append(curr)
        return ans
    
    return app