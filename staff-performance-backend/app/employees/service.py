from google.cloud import firestore
from app.common.security import hash_password
from typing import Optional

def create_employee(db: firestore.Client, employee_data: dict):
    users_ref = db.collection("users")
    
    # Check if email exists
    existing = users_ref.where("email", "==", employee_data["email"]).limit(1).stream()
    if any(existing):
        return False, "Email already exists", None
    
    # Check if employeeId exists
    existing_id = users_ref.where("employeeId", "==", employee_data["employeeId"]).limit(1).stream()
    if any(existing_id):
        return False, "Employee ID already exists", None
    
    # Hash password
    employee_data["password"] = hash_password(employee_data["password"])
    
    # Create document
    doc_ref = users_ref.document()
    doc_ref.set(employee_data)
    
    return True, "Employee created successfully", doc_ref.id

def get_all_employees(db: firestore.Client, role_filter=None, status_filter=None):
    users_ref = db.collection("users")
    query = users_ref
    
    if role_filter:
        query = query.where("role", "==", role_filter)
    if status_filter:
        query = query.where("status", "==", status_filter)
    
    employees = []
    for doc in query.stream():
        data = doc.to_dict()
        if data:
            data.pop("password", None)
            data["id"] = doc.id
            employees.append(data)
    
    return employees

def get_employee_by_id(db: firestore.Client, doc_id: str):
    doc_ref = db.collection("users").document(doc_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
    
    data = doc.to_dict()
    if data:
        data.pop("password", None)
        data["id"] = doc.id
    
    return data

def update_employee(db: firestore.Client, doc_id: str, update_data: dict):
    doc_ref = db.collection("users").document(doc_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False, "Employee not found"
    
    update_data = {k: v for k, v in update_data.items() if v is not None}
    if not update_data:
        return False, "No data to update"
    
    doc_ref.update(update_data)
    return True, "Employee updated successfully"

def delete_employee(db: firestore.Client, doc_id: str):
    doc_ref = db.collection("users").document(doc_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False, "Employee not found"
    
    doc_ref.update({"status": "inactive"})
    return True, "Employee deactivated successfully"

def reset_employee_password(db: firestore.Client, doc_id: str, new_password: str):
    doc_ref = db.collection("users").document(doc_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False, "Employee not found"
    
    hashed_password = hash_password(new_password)
    doc_ref.update({"password": hashed_password})
    return True, "Password reset successfully"
