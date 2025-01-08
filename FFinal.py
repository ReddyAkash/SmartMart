import time
from ultralytics import YOLO
import cv2
import cvzone
import math
from sort import Sort
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from docxtpl import DocxTemplate
import datetime
import numpy as np
import pypyodbc as odbc
import pyodbc
#from credential import username, password
from credentials import username, password

server = 'fullkrt.database.windows.net'
database = 'FullKart'
connection_string = 'Driver={ODBC Driver 18 for SQL Server};Server='+server+';Database='+database+';Uid='+username+';Pwd='+password+';'
conn = odbc.connect(connection_string)

# Create a new Tkinter window
window = tk.Tk()
window.title("BILLING SYSTEM")
window.configure(bg="#DF2E38")  # Set background color for the window

# Create labels and entry fields for customer details
customer_name_label = tk.Label(window, text="Customer Name:", bg="#DF2E38", fg="white", font=("Arial", 12))
customer_name_label.pack(padx=20, pady=5, anchor="w")

customer_name_entry = tk.Entry(window, font=("Arial", 12))
customer_name_entry.pack(padx=20, pady=5)

customer_mobile_label = tk.Label(window, text="Mobile Number:", bg="#DF2E38", fg="white", font=("Arial", 12))
customer_mobile_label.pack(padx=20, pady=5, anchor="w")

customer_mobile_entry = tk.Entry(window, font=("Arial", 12))
customer_mobile_entry.pack(padx=20, pady=5)

# Create the Treeview widget for the table
tree = ttk.Treeview(window, columns=("Qty", "Description", "Price", "Remove"), show="headings", selectmode="browse")
tree.heading("Qty", text="Qty")
tree.heading("Description", text="Description")
tree.heading("Price", text="Price")
tree.heading("Remove", text="Remove")

tree.column("Qty", width=50, anchor="center")
tree.column("Description", width=200, anchor="w")
tree.column("Price", width=100, anchor="w")
tree.column("Remove", width=50, anchor="center")

# Create a Scrollbar widget
scrollbar = ttk.Scrollbar(window, orient="vertical", command=tree.yview)

# Configure the Treeview to use the scrollbar
tree.configure(yscrollcommand=scrollbar.set)

# Pack the Treeview and Scrollbar
tree.pack(expand=True, padx=20, pady=10)
scrollbar.pack(side="right")

# Create a label to display the total count
totalcount_label = tk.Label(window, text="Total Amount: ", bg="#F0F0F0", fg="#333333", font=("Arial", 14))
totalcount_label.pack(side="bottom", fill="x", padx=20, pady=10)
totalcount_lab = tk.Label(window, text="Quantity: ", bg="#F0F0F0", fg="#333333", font=("Arial", 14))
totalcount_lab.pack(side="right", fill="x", padx=20, pady=10)

tree.pack()

# Function to fetch product names from the database
def fetch_product_names_from_db():
    try:
        cursor = conn.cursor()
        sql = "SELECT PRODUCTNAME FROM PRODUCTS"
        cursor.execute(sql)
        product_names = [row[0] for row in cursor.fetchall()]  # Fetch all product names
        return product_names
    except Exception as e:
        print(f"Error fetching product names: {e}")
        return []

# Define the class names
classNames = fetch_product_names_from_db()

# Dynamically create a dictionary to store lists for each product
product_lists = {name: [] for name in classNames}

detected_products = []

# Function to fetch product price and other details
def fetch_product_details_from_db(product_name):
    try:
        cursor = conn.cursor()
        query = f"SELECT price FROM Products WHERE productname = '{product_name}'"
        cursor.execute(query)
        result = cursor.fetchone()
        if result:
            return result[0]  # Assuming price is in the first column
        else:
            return None
    except Exception as e:
        print(f"Error fetching product details: {e}")
        return None

# Function to fetch available stock for a product
def fetch_available_stock(product_name):
    sql = f"SELECT qty FROM PRODUCTs WHERE PRODUCTNAME = '{product_name}'"
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        return result[0] if result else -1  # Return 0 if no result
    except Exception as e:
        print(f"Error fetching product details: {e}")
        return None

# Dictionary to store and temporarily decrease stock in real-time for each product
temp_stock = {product_name: fetch_available_stock(product_name) for product_name in list(classNames)}

# Function to insert a customer if they don't already exist and return their CustomerID
def insert_customer_if_not_exists(customer_name):
    cursor = conn.cursor()
    # Check if the customer already exists
    cursor.execute("SELECT CustomerID FROM Customers WHERE CustomerName = ?", (customer_name,))
    result = cursor.fetchone()
    if result:
        print(f"Customer found: {customer_name} with CustomerID: {result[0]}")
        return result[0]  # CustomerID exists, return it
    else:
        # Insert new customer and get the generated CustomerID
        cursor.execute("INSERT INTO Customers (CustomerName) VALUES (?)", (customer_name,))
        conn.commit()
        new_customer_id = cursor.lastrowid
        print(f"New customer created: {customer_name} with CustomerID: {new_customer_id}")
        return new_customer_id  # Return the newly created CustomerID

def store_word_file(customer_id, file_name):
    with open(file_name, 'rb') as file:
        document_data = file.read()  # Read the file as binary data

    try:
        print("Entering the try block...")  # This will tell us if the try block was reached.
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Documents (CustomerID, Document, CreatedDate)
            VALUES (?, ?, ?)
        """, (customer_id, pyodbc.Binary(document_data), datetime.datetime.now()))
        print("...2")
        conn.commit()
        print("...3")
        print(f"Document saved for CustomerID: {customer_id} with file name: {file_name}")
    except Exception as e:
        print(f"Error storing document: {e}")

# Function to update the product quantities in the database
def update_product_inventory(products):
    for product in products:
        name = product['name']
        quantity = product['quantity']
        try:
            # Example SQL command to update the inventory
            sql_query = f"UPDATE products SET qty = qty - {quantity} WHERE productname = '{name}'"
        
            cursor = conn.cursor()
            cursor.execute(sql_query)
            conn.commit()
        except Exception as e:
            print(f"Error updating inventory for {name}: {e}")

# Function to generate the invoice and store the document with correct CustomerID
def generate_invoice():
    customer_name = customer_name_entry.get()
    customer_mobile = customer_mobile_entry.get()

    if not customer_name or not customer_mobile:
        messagebox.showerror("Error", "Please enter customer details.")
        return

    # Insert the customer or get the existing one
    customer_id = insert_customer_if_not_exists(customer_name)
    if not customer_id:
        messagebox.showerror("Error", "Unable to create or retrieve customer.")
        return

    print(f"Using CustomerID: {customer_id} for the document generation.")

    # Load the invoice template
    # -----------------------------
    doc = DocxTemplate("SmartMart/invoice_template.docx")

    # Get the products and their details from the treeview
    tree_items = tree.get_children()
    products = []
    total = 0
    for item in tree_items:
        # Get the product data from each tree item
        product = tree.item(item)['values']
        quantity = product[0]  # Extract the quantity
        name = product[1]      # Extract the product name
        price_str = product[2] # Extract the price

        # Convert price to float and calculate total price
        price_value = float(price_str.split('₹')[-1])  # Assuming price is like "10"
        total += price_value

        # Append the product details to the products list
        products.append({
            "name": name,
            "quantity": quantity,
            "price": price_value/quantity,  # Keep as string for display
            "total_price": price_value  # Include total price for each product
        })

    # Create context for the invoice template
    context = {
        "customer_name": customer_name,
        "customer_mobile": customer_mobile,
        "products": products,
        "totalcount": total
    }

    try:
        # Render the template with the detected products
        doc.render(context)

        # Save the generated invoice locally
        doc_name = f"bill_{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.docx"
        doc.save(doc_name)

        print(f"Invoice generated: {doc_name}")

        # Store the invoice in the database with the CustomerID
        store_word_file(customer_id, doc_name)

        # Update the inventory after generating the invoice
        update_product_inventory(products)

        messagebox.showinfo("Invoice Complete", "Invoice generated successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
        print(e)

# Create a button to generate the invoice
get_invoice_button = tk.Button(window, text="Get Invoice", command=generate_invoice, bg="#4CAF50", fg="white",
                               font=("Arial", 12), relief="raised")
get_invoice_button.pack(pady=10)

# Function to fetch documents for a specific customer
def fetch_documents_for_customer(customer_name):
    try:
        cursor = conn.cursor()
        # Fetch documents based on the customer name
        cursor.execute("""
            SELECT d.DocumentID, d.CreatedDate, d.Document 
            FROM Documents d
            JOIN Customers c ON d.CustomerID = c.CustomerID
            WHERE c.CustomerName = ?
        """, (customer_name,))
        return cursor.fetchall()  # Returns a list of tuples (DocumentID, Document)
    except Exception as e:
        print(f"Error fetching documents: {e}")
        return []

# Function to insert a customer if they don't already exist and return their CustomerID
def insert_customer_if_not_exists(customer_name):
    cursor = conn.cursor()
    # Check if the customer already exists
    cursor.execute("SELECT CustomerID FROM Customers WHERE CustomerName = ?", (customer_name,))
    result = cursor.fetchone()
    if result:
        return result[0]  # CustomerID exists, return it
    else:
        # Insert new customer and get the generated CustomerID
        cursor.execute("INSERT INTO Customers (CustomerName) VALUES (?)", (customer_name,))
        conn.commit()
        return cursor.lastrowid  # Return the newly created CustomerID

# Function to save the document file locally
def save_document(document_id, document_data):
    try:
        # Specify the file name and path
        file_path = f"document_{document_id}.docx"
        with open(file_path, 'wb') as file:
            file.write(document_data)
        messagebox.showinfo("Success", f"Document saved as {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save document: {e}")

# Function to open a new window with a search feature
def open_new_window():
    # Create a new top-level window
    new_window = tk.Toplevel(window)
    new_window.title("Search Customer Documents")  # Set the title of the new window
    new_window.geometry("400x300")  # Set size of the new window

    # Add a label for the search bar
    search_label = tk.Label(new_window, text="Search Customer:", font=("Arial", 12))
    search_label.pack(pady=10)

    # Add an entry widget for searching customers
    search_entry = tk.Entry(new_window, font=("Arial", 12))
    search_entry.pack(pady=5)

    # Create a treeview to display documents
    tree = ttk.Treeview(new_window, columns=("CreatedDate", "Download"), show="headings")
    tree.heading("CreatedDate", text="Date and Time")
    tree.heading("Download", text="Action")
    tree.column("CreatedDate", width=150, anchor="center")
    tree.column("Download", width=100, anchor="center")
    tree.pack(pady=10, fill="both", expand=True)

    # Function to perform the search
    def search_customer(event=None):
        customer_name = search_entry.get()
        if not customer_name:
            messagebox.showwarning("Input Error", "Please enter a customer name.")
            return

        # Clear existing treeview data
        tree.delete(*tree.get_children())

        # Fetch documents for the entered customer name
        documents = fetch_documents_for_customer(customer_name)
        if documents:
            # Insert documents into the treeview
            for doc_id, created_date, document in documents:
                formatted_date = created_date.strftime("%Y-%m-%d %H:%M:%S")
                tree.insert("", "end", values=(formatted_date, "Download"), iid=doc_id)
        else:
            messagebox.showinfo("No Results", f"No documents found for customer '{customer_name}'.")

    # Bind the Enter key to the search function
    search_entry.bind('<Return>', search_customer)

    # Add a button to trigger the search
    search_button = tk.Button(new_window, text="Search", command=search_customer, bg="#4CAF50", fg="white")
    search_button.pack(pady=10)

    # Function to handle the download action
    def on_download(event):
        selected_item = tree.selection()
        if selected_item:
            doc_id = selected_item[0]  # Get the selected document ID
            # Fetch the document data from the database
            cursor = conn.cursor()
            cursor.execute("SELECT Document FROM Documents WHERE DocumentID = ?", (doc_id,))
            document_data = cursor.fetchone()
            if document_data:
                save_document(doc_id, document_data[0])  # Save the document
            else:
                messagebox.showwarning("Error", "Document not found.")

    # Bind the treeview item double-click to the download function
    tree.bind('<Double-1>', on_download)

    # Example button to close the new window
    close_button = tk.Button(new_window, text="Close", command=new_window.destroy, bg="#f44336", fg="white")
    close_button.pack(pady=10)

# Create another button to open the new window
open_window_button = tk.Button(window, text="Past Records", command=open_new_window, bg="#2196F3", fg="white",
                               font=("Arial", 12), relief="raised")
open_window_button.pack(pady=10)

# Data structure to store what's in the tree
current_tree_data = {}

# Function to update data in the Treeview
def update_data(detected_products):
    # Clear the existing data in the Treeview
    tree.delete(*tree.get_children())

    total = 0
    total_count = 0
    data = []

    # Using a set to avoid counting duplicates and get unique product names
    unique_products = set(detected_products)
    
    for product_name in unique_products:
        qty = detected_products.count(product_name)
        price = fetch_product_details_from_db(product_name)
        total_price = qty * price
        total += total_price
        total_count += qty
        data.append((qty, product_name.capitalize(), f"₹{total_price}"))

        # Track current data in the tree
        current_tree_data[product_name] = qty

    # Add rows to Treeview, including a 'Remove' label for each row
    for row in data:
        tree.insert("", "end", values=(*row, "x"))

    # Update the total count and amount labels
    totalcount_label.config(text="Total Amount: ₹" + str(total), font=("Arial", 14))
    totalcount_lab.config(text="Total Count: " + str(sum([row[0] for row in data])), font=("Arial", 14))

# Function to handle row removal (decrement or remove)
def remove_item(event):
    selected_item = tree.selection()

    if selected_item:
        item = selected_item[0]  # Get the first selected row ID
        values = tree.item(item, "values")  # Get the values from the selected row
        product_name = values[1].lower()  # Get the product name from the row (lowercase to match the dict)

        # Fetch the current quantity in the treeview for this item
        current_qty = current_tree_data.get(product_name, 0)

        # If more than one quantity, decrement it
        if current_qty > 1:
            new_qty = current_qty - 1
            price = fetch_product_details_from_db(product_name)
            new_total_price = new_qty * price

            # Update the row with the new quantity and price
            tree.item(item, values=(new_qty, product_name.capitalize(), f"₹{new_total_price}", "x"))
            current_tree_data[product_name] = new_qty

            # Update the detected_products list (remove one instance)
            detected_products.remove(product_name)

            # Update temp_stock
            temp_stock[product_name] += 1
            
        else:
            # If only one quantity, remove the row entirely
            tree.delete(item)
            del current_tree_data[product_name]  # Remove from tracking

            # Remove all instances of the product from detected_products
            detected_products[:] = [p for p in detected_products if p != product_name]

            # Update temp_stock
            temp_stock[product_name] += 1

        # After removing or updating, update the total count and amount
        update_totals()

# Function to update total amount and count
def update_totals():
    total = 0
    total_count = 0

    for product_name, qty in current_tree_data.items():
        price = fetch_product_details_from_db(product_name)
        total += qty * price
        total_count += qty

    totalcount_label.config(text="Total Amount: ₹" + str(total), font=("Arial", 14))
    totalcount_lab.config(text="Total Count: " + str(total_count), font=("Arial", 14))

# Bind the click event to the 'Remove' column (last column)
tree.bind("<ButtonRelease-1>", remove_item)

# Error view
def error_view(qty, available_stock, product_name):
    messagebox.showerror("Error", f"{product_name} exceeds available qty of {available_stock} by {qty - available_stock}")

# Set up the video capture
#url = 'http://192.168.190.134:81/stream'
cap = cv2.VideoCapture(0)
cap.set(3, 1440)
cap.set(4, 826)

# Load the YOLO model
#model = YOLO('fullkart.pt')
model = YOLO('SmartMart/best.pt').to('cuda')

# Create the object tracker
tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)

# Initialize a dictionary to track object IDs and their detection time
object_detection_time = {}

# Set a threshold for stable detection time (e.g., 5 seconds)
detection_threshold = 3  # seconds

# Initialize a dictionary to track object exit times
object_exit_time = {}

# Set a threshold for object disappearance duration (e.g., 5 seconds)
timeout_threshold = 1  # seconds

# Set a limit for products
object_limit = 3

object_info = {}

# Main loop to capture video and detect objects
while True:
    
    success, img = cap.read()
    
    results = model(img, stream=True)  # Assume this is your detection model
    detections = np.empty((0, 5))

    # Initialize a counter for current frame detected objects
    detected_in_frame = 0

    # Detect objects and collect bounding box information
    current_frame_objects = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            w, h = x2 - x1, y2 - y1
            conf = math.ceil((box.conf[0] * 100)) / 100  # Confidence
            cls = int(box.cls[0])  # Class index
            currentClass = classNames[cls]  # Class name

            detected_in_frame += 1

            # If limit is exceeded, skip adding more objects but don't stop execution
            if detected_in_frame > object_limit:
                break

            # Collect bounding box information for current frame
            currentArray = np.array([x1, y1, x2, y2, conf])
            detections = np.vstack((detections, currentArray))

            # Store current detection info to link with tracker later
            current_frame_objects.append({
                "bbox": [x1, y1, x2, y2],
                "class": currentClass,
                "confidence": conf
            })

    # Check if object limit is exceeded
    if detected_in_frame > object_limit:
        cv2.putText(img, "Object limit exceeded!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        #continue
    else:
        cv2.putText(img, "Detecting...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Update tracker
        resultsTracker = tracker.update(detections)

        # Update tracked object information with ID, class, and confidence
        for result in resultsTracker:
            x1, y1, x2, y2, obj_id = result
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            w, h = x2 - x1, y2 - y1
            cx, cy = x1 + w // 2, y1 + h // 2

            # Find the matching detection for the tracked object
            best_match_class = "Unknown"
            best_match_conf = 0.0
            for obj in current_frame_objects:
                detection_bbox = obj["bbox"]
                if np.allclose([x1, y1, x2, y2], detection_bbox, atol=10):
                    best_match_class = obj["class"]
                    best_match_conf = obj["confidence"]
                    break

            # Check if the object ID was previously tracked
            if obj_id in object_exit_time:
                time_since_exit = time.time() - object_exit_time[obj_id]
                # If the object was gone for longer than the threshold, reset its ID
                if time_since_exit > timeout_threshold:
                    obj_id = max(object_exit_time.keys(), default=0) + 1

            # Store or update the object info with the correct class and confidence
            object_info[obj_id] = (best_match_class, best_match_conf)

            # Track detection time
            if obj_id not in object_detection_time:
                # If obj_id is new, add it with the current time
                object_detection_time[obj_id] = time.time()
            else:
                elapsed_time = time.time() - object_detection_time[obj_id]
    
                # Only update if the object has been detected for the threshold duration
                if elapsed_time > detection_threshold:
                    tracked_class, tracked_conf = object_info.get(obj_id, ("Unknown", 0.0))

                    if tracked_class in product_lists and obj_id not in product_lists[tracked_class]:
                        product_lists[tracked_class].append(obj_id)

                        # Check stock availability at the moment of detection
                        available_stock = temp_stock.get(tracked_class, 0)

                        # Count occurrences of the tracked class in detected_products
                        current_qty = detected_products.count(tracked_class)
                        
                        if available_stock <= 0:
                            print(f"Insufficient stock for {tracked_class}, skipping detection.")
                            error_view(current_qty, available_stock, tracked_class)
                            continue

                        if current_qty > available_stock:
                        #if current_qty >= available_stock:
                            # Already detected the max number of products for this class
                            print(f"Product {tracked_class} already detected {current_qty} times, cannot add more.")
                            continue

                        # Add to detected_products only if stock is available and count is valid
                        detected_products.append(tracked_class)
                        temp_stock[tracked_class] -= 1  # Decrease stock only when product is added
                        print(f"Product detected: {tracked_class}, Stock updated: {temp_stock[tracked_class]}")                    

                # If the object is gone (tracker doesn't detect it), remove it from object_exit_time
                object_exit_time[obj_id] = time.time()

                # Clean up: If the object has been gone longer than the disappearance threshold, remove it
                for obj_id, exit_time in list(object_exit_time.items()):
                    if time.time() - exit_time > timeout_threshold:
                        del object_detection_time[obj_id]
                        del object_exit_time[obj_id]
                        if obj_id in object_info:
                            del object_info[obj_id]

            # Draw bounding box and label
            cvzone.cornerRect(img, (x1, y1, w, h), l=9, rt=2, colorR=(255, 0, 255))
            cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)
            cvzone.putTextRect(img, f'{best_match_class} {best_match_conf}', (max(0, x1), max(35, y1 + 35)), scale=1, thickness=1)
            update_data(detected_products)

    # Clean up expired object IDs
    for obj_id in list(object_exit_time.keys()):
        if time.time() - object_exit_time[obj_id] > timeout_threshold:
            del object_exit_time[obj_id]

    window.update()
    
    # Display the frame
    cv2.imshow('Image', img)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

window.mainloop()
cap.release()
cv2.destroyAllWindows()