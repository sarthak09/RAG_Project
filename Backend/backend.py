from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from auth.hash import hash_password, verify_password
from auth.validators import is_valid_email, is_strong_password
from auth.jwt_handler import create_token, verify_token
from utils.file_ops import load_users, save_users
from utils.token_blacklist import blacklist_token, is_token_blacklisted
from werkzeug.utils import secure_filename
import os
import time
import shutil
from pathlib import Path
from ai.constant import *
from ai.llm import LLM
from ai.vectorstore import VectorDB
from ai.normal_chain import build_rag_chain
from ai.embed import Embedder

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
CORS(app, origins=["http://localhost:5173"])

UPLOAD_FOLDER = Path(".data/uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

llm_instance = None
vdb_instance = None
emb_instance = None

user_processing_status = {}

def cleanup_user_data(email):
    """Clean up vector DB and registry for a user"""
    try:
        # Delete vector DB directory (includes user-specific registry.json)
        user_db_dir = f"./db/{email.replace('@', '_at_').replace('.', '_')}"
        if os.path.exists(user_db_dir):
            # Force close any open connections by removing the directory
            for i in range(3):  # Try 3 times
                try:
                    shutil.rmtree(user_db_dir)
                    print(f"Deleted vector DB and registry for {email}")
                    break
                except Exception as e:
                    if i < 2:
                        time.sleep(0.5)  # Wait before retry
                    else:
                        print(f"Error deleting vector DB after retries: {e}")
        
        # Wait to ensure file system has released locks
        time.sleep(0.5)
        
    except Exception as e:
        print(f"Error in cleanup_user_data: {e}")

def initialize_rag_system():
    global llm_instance, vdb_instance, emb_instance
    llm_instance = LLM(LLMNAME)
    emb_instance = Embedder(EMBEDNAME).emb
    print("RAG system components initialized successfully")

def get_user_rag_db(email, semantic=False):
    user_db_dir = f"./db/{email.replace('@', '_at_').replace('.', '_')}"
    user_registry = f"{user_db_dir}/registry.json"
    vdb = VectorDB(embedding=emb_instance, persist_directory=user_db_dir, batch_size=CHUNK_SIZE, semantic=semantic, registry_path=user_registry)
    return vdb

def get_user_folder(email):
    user_folder = UPLOAD_FOLDER / email.replace('@', '_at_').replace('.', '_')
    user_folder.mkdir(exist_ok=True)
    return user_folder

def get_user_from_token(token):
    if not token:
        return None
    token = token.replace("Bearer ", "")
    if is_token_blacklisted(token):
        return None
    payload = verify_token(token)
    return payload.get("email") if payload else None

@app.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        address1 = data.get("address1")
        address2 = data.get("address2")
        city = data.get("city")
        state = data.get("state")
        zip = data.get("zip")
        if not email or not password:
            return jsonify({"error": "Email & password required"}), 400
        if not is_valid_email(email):
            return jsonify({"error": "Invalid email"}), 400
        if not is_strong_password(password):
            return jsonify({"error": "Weak password"}), 400
        users = load_users()
        if any(u["email"] == email for u in users["users"]):
            return jsonify({"error": "Email already in use"}), 409
        from datetime import datetime, timedelta
        trial_end_date = (datetime.utcnow() + timedelta(days=14)).isoformat()
        hashed = hash_password(password)
        users["users"].append({
            "email": email, 
            "password": hashed, 
            "name": name, 
            "address1": address1, 
            "address2": address2, 
            "city": city, 
            "state": state, 
            "zip": zip,
            "trial_end_date": trial_end_date,
            "created_at": datetime.utcnow().isoformat()
        })
        save_users(users)
        return jsonify({"success": True}), 201
    except Exception as e:
        print("Server error:", e)
        return jsonify({"error": "Internal server error", "success": False}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return jsonify({"error": "Email & password required"}), 400
        users = load_users()
        user = next((u for u in users["users"] if u["email"] == email), None)
        if not user or not verify_password(password, user["password"]):
            return jsonify({"error": "Invalid credentials"}), 401
        from datetime import datetime
        trial_end = datetime.fromisoformat(user.get("trial_end_date"))
        is_trial_active = datetime.utcnow() < trial_end
        token = create_token(email)
        return jsonify({
            "success": True, 
            "token": token, 
            "name": user["name"],
            "email": user["email"],
            "trial_active": is_trial_active,
            "trial_end_date": user.get("trial_end_date")
        }), 200
    except Exception as e:
        print("Login error:", e)
        return jsonify({"error": "Internal server error","success": False}), 500

@app.route("/signout", methods=["POST"])
def signout():
    try:
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token required"}), 400
        token = token.replace("Bearer ", "")
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Invalid token"}), 401
        email = payload.get("email")
        if email:
            user_folder = get_user_folder(email)
            if user_folder.exists():
                shutil.rmtree(user_folder)
            
            # Clean up vector DB and registry
            cleanup_user_data(email)
            
            if email in user_processing_status:
                del user_processing_status[email]
        blacklist_token(token)
        return jsonify({"success": True}), 200
    except Exception as e:
        print("Logout error:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/verify", methods=["GET"])
def verify():
    try:
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token required", "valid": False}), 401
        token = token.replace("Bearer ", "")
        if is_token_blacklisted(token):
            return jsonify({"error": "Token has been revoked", "valid": False}), 401
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token", "valid": False}), 401
        users = load_users()
        user = next((u for u in users["users"] if u["email"] == payload["email"]), None)
        if not user:
            return jsonify({"error": "User not found", "valid": False}), 404
        from datetime import datetime
        trial_end = datetime.fromisoformat(user.get("trial_end_date"))
        is_trial_active = datetime.utcnow() < trial_end
        return jsonify({
            "valid": True,
            "email": user["email"],
            "name": user["name"],
            "trial_active": is_trial_active,
            "trial_end_date": user.get("trial_end_date")
        }), 200
    except Exception as e:
        print("Verify error:", e)
        return jsonify({"error": "Internal server error", "valid": False}), 500

@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized"}), 401
        
        if 'files' not in request.files:
            return jsonify({"error": "No files provided"}), 400
        
        files = request.files.getlist('files')
        user_folder = get_user_folder(email)
        existing_files = list(user_folder.glob("*.pdf"))
        
        # Check if user is at file limit
        if len(existing_files) >= MAX_FILES_PER_USER and len(files) > 0:
            # Remove oldest files to make room for new ones
            for existing_file in existing_files:
                existing_file.unlink()
        
        # Clear processing status
        if email in user_processing_status:
            del user_processing_status[email]
        
        # Clean up vector DB and registry
        cleanup_user_data(email)
        
        uploaded = []
        files_processed = 0
        
        for file in files:
            if files_processed >= MAX_FILES_PER_USER:
                break
                
            if file.filename and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                filepath = user_folder / filename
                file.save(str(filepath))
                uploaded.append(filename)
                files_processed += 1
        
        return jsonify({"success": True, "uploaded": uploaded}), 200
    except Exception as e:
        print("Upload error:", e)
        return jsonify({"error": "Upload failed"}), 500


@app.route("/files", methods=["GET"])
def list_files():
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized"}), 401
        user_folder = get_user_folder(email)
        files = []
        for pdf_file in user_folder.glob("*.pdf"):
            size = pdf_file.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
            files.append({
                "name": pdf_file.name,
                "size": size_str
            })
        return jsonify({"files": files}), 200
    except Exception as e:
        print("List files error:", e)
        return jsonify({"error": "Failed to list files"}), 500

@app.route("/files/<filename>", methods=["DELETE"])
def delete_file(filename):
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized"}), 401
        user_folder = get_user_folder(email)
        filepath = user_folder / secure_filename(filename)
        if filepath.exists():
            filepath.unlink()
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        print("Delete error:", e)
        return jsonify({"error": "Delete failed"}), 500

@app.route("/rag-status", methods=["GET"])
def get_rag_status():
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized"}), 401
        status = user_processing_status.get(email, {})
        return jsonify({
            "status": status.get("status", "not_started"),
            "chunking_method": status.get("chunking_method", "standard"),
            "hybrid_search": status.get("hybrid_search", False),
            "message": status.get("message", "")
        }), 200
    except Exception as e:
        print("RAG status error:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/process-document", methods=["POST"])
def process_document():
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json()
        chunking_method = data.get("chunking_method", "standard")
        hybrid_search = data.get("hybrid_search", False)
        user_folder = get_user_folder(email)
        pdf_files = list(user_folder.glob("*.pdf"))
        if not pdf_files:
            return jsonify({"error": "No PDF file found"}), 400
        search_type = "hybrid search" if hybrid_search else "dense search"
        user_processing_status[email] = {
            "status": "processing",
            "chunking_method": chunking_method,
            "hybrid_search": hybrid_search,
            "message": f"Processing with {chunking_method} chunking and {search_type}..."
        }
        try:
            # Clean vector database and registry before processing
            cleanup_user_data(email)
            
            semantic = (chunking_method == "semantic")
            user_vdb = get_user_rag_db(email, semantic=semantic)
            
            pdf_file = pdf_files[0]
            user_vdb.ingest_file_incremental(str(pdf_file))
            search_type = "hybrid search" if hybrid_search else "dense search"
            user_processing_status[email] = {
                "status": "ready",
                "chunking_method": chunking_method,
                "hybrid_search": hybrid_search,
                "message": f"Document processed successfully with {chunking_method} chunking and {search_type}"
            }
            return jsonify({"success": True, "message": "Document processed successfully"}), 200
        except Exception as processing_error:
            print("Document processing error:", processing_error)
            user_processing_status[email] = {
                "status": "error",
                "chunking_method": chunking_method,
                "hybrid_search": hybrid_search,
                "message": f"Processing failed: {str(processing_error)}"
            }
            return jsonify({"error": "Document processing failed"}), 500

    except Exception as e:
        print("Process document error:", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/query", methods=["POST"])
def query_document():
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized"}), 401        # Check if document is processed
        status = user_processing_status.get(email, {})
        if status.get("status") != "ready":
            return jsonify({"error": "Document not ready. Please process the document first."}), 400
        data = request.get_json()
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "Question is required"}), 400
        chunking_method = status.get("chunking_method", "standard")
        hybrid_search = status.get("hybrid_search", False)
        semantic = (chunking_method == "semantic")
        user_vdb = get_user_rag_db(email, semantic=semantic)
        retriever = user_vdb.get_retriever(use_hybrid=hybrid_search, k=4)
        rag_chain = build_rag_chain(llm_instance, retriever)
        result = rag_chain.invoke(question)
        return jsonify({
            "success": True,
            "answer": result["answer"],
            "context": result["context_text"],
            "source_docs": len(result["context_docs"]),
            "retrieval_method": "Hybrid (Dense + BM25)" if hybrid_search else "Dense Only",
            "chunking_method": chunking_method
        }), 200
    except Exception as e:
        print("Query error:", e)
        return jsonify({"error": "Failed to process query"}), 500
    
@app.route('/')
def serve_react():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    initialize_rag_system()
    app.run(host='0.0.0.0', port=5000, debug=True)
    print("Server running on http://localhost:5000")