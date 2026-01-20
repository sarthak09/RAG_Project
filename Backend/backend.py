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
from ai.reranker import Reranker
import importlib
import ai.reranker

app = Flask(__name__, static_folder='../Frontend/dist', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
# CORS(app, origins=["http://localhost:5173"])

UPLOAD_FOLDER = Path(".data/uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

llm_instance = None
vdb_instance = None
emb_instance = None

user_processing_status = {}

def cleanup_user_data(email, force=False):
    """Clean up vector DB and registry for a user"""
    try:
        user_db_dir = f"./db/{email.replace('@', '_at_').replace('.', '_')}"
        
        if not os.path.exists(user_db_dir):
            print(f"No database to clean for {email}")
            return True
            
        print(f"Starting cleanup for {email}...")
        
        # Force close any open connections by removing the directory
        max_retries = 10 if force else 5
        for i in range(max_retries):
            try:
                # Change permissions on all files
                for root, dirs, files in os.walk(user_db_dir):
                    for d in dirs:
                        try:
                            os.chmod(os.path.join(root, d), 0o777)
                        except:
                            pass
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            os.chmod(file_path, 0o777)
                            # Remove readonly flag on Windows
                            if os.name == 'nt':
                                os.system(f'attrib -r "{file_path}"')
                        except:
                            pass
                
                # Try to remove the directory
                shutil.rmtree(user_db_dir)
                print(f"âœ“ Deleted vector DB and registry for {email}")
                time.sleep(0.5)  # Brief pause after successful deletion
                return True
                
            except PermissionError as e:
                wait_time = 1.0 * (i + 1)  # Linear backoff
                if i < max_retries - 1:
                    print(f"Database locked (attempt {i+1}/{max_retries}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Could not delete database after {max_retries} retries")
                    # Last resort: rename the directory
                    try:
                        backup_name = f"{user_db_dir}_old_{int(time.time())}"
                        os.rename(user_db_dir, backup_name)
                        print(f"âœ“ Moved locked database to {backup_name}")
                        return True
                    except Exception as rename_error:
                        print(f"âœ— Failed to rename database: {rename_error}")
                        return False
                        
            except Exception as e:
                wait_time = 1.0 * (i + 1)
                if i < max_retries - 1:
                    print(f"Error during cleanup (attempt {i+1}/{max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    print(f"âœ— Cleanup failed after {max_retries} retries: {e}")
                    return False
        
        return False
        
    except Exception as e:
        print(f"âœ— Error in cleanup_user_data: {e}")
        return False

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
            return jsonify({"error": "Token required", "success": False}), 400
        
        token = token.replace("Bearer ", "")
        payload = verify_token(token)
        
        if not payload:
            return jsonify({"error": "Invalid token", "success": False}), 401
        
        email = payload.get("email")
        
        if email:
            print(f"Signing out user: {email}")
            
            # Delete user files
            user_folder = get_user_folder(email)
            if user_folder.exists():
                try:
                    shutil.rmtree(user_folder)
                    print(f"âœ“ Deleted user files for {email}")
                except Exception as e:
                    print(f"âš  Error deleting user files: {e}")
            
            # Clean up vector DB and registry (force cleanup)
            cleanup_success = cleanup_user_data(email, force=True)
            if cleanup_success:
                print(f"âœ“ Cleaned up vector DB for {email}")
            else:
                print(f"âš  Partial cleanup for {email}")
            
            # Clear processing status
            if email in user_processing_status:
                del user_processing_status[email]
                print(f"âœ“ Cleared processing status for {email}")
        
        # Blacklist the token
        blacklist_token(token)
        print(f"âœ“ Token blacklisted")
        
        return jsonify({"success": True, "message": "Signed out successfully"}), 200
        
    except Exception as e:
        print(f"âœ— Logout error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Logout failed", "success": False}), 500

@app.route("/check-email", methods=["POST"])
def check_email():
    try:
        data = request.get_json()
        email = data.get("email")
        
        if not email:
            return jsonify({"error": "Email required"}), 400
        
        if not is_valid_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        users = load_users()
        user = next((u for u in users["users"] if u["email"] == email), None)
        
        if not user:
            return jsonify({"error": "Email not found", "success": False}), 404
        
        return jsonify({"success": True, "message": "Email verified"}), 200
        
    except Exception as e:
        print("Check email error:", e)
        return jsonify({"error": "Internal server error", "success": False}), 500

@app.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json()
        email = data.get("email")
        new_password = data.get("new_password")
        
        if not email or not new_password:
            return jsonify({"error": "Email and new password required"}), 400
        
        if not is_valid_email(email):
            return jsonify({"error": "Invalid email"}), 400
        
        if not is_strong_password(new_password):
            return jsonify({"error": "Password does not meet requirements"}), 400
        
        users = load_users()
        user = next((u for u in users["users"] if u["email"] == email), None)
        
        if not user:
            return jsonify({"error": "Email not found", "success": False}), 404
        
        # Update password
        user["password"] = hash_password(new_password)
        save_users(users)
        
        return jsonify({"success": True, "message": "Password reset successfully"}), 200
        
    except Exception as e:
        print("Reset password error:", e)
        return jsonify({"error": "Internal server error", "success": False}), 500

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
            return jsonify({"error": "Unauthorized", "success": False}), 401
        
        if 'files' not in request.files:
            return jsonify({"error": "No files provided", "success": False}), 400
        
        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({"error": "No files provided", "success": False}), 400
        
        user_folder = get_user_folder(email)
        existing_files = list(user_folder.glob("*.pdf"))
        
        # If there are existing files or processing status, clean everything up
        if len(existing_files) > 0 or email in user_processing_status:
            print(f"Cleaning up existing data for {email} before upload...")
            
            # Clear processing status first
            if email in user_processing_status:
                del user_processing_status[email]
            
            # Clean up vector DB and registry (force cleanup)
            cleanup_success = cleanup_user_data(email, force=True)
            if not cleanup_success:
                return jsonify({
                    "error": "Failed to cleanup existing data. Please try again in a few seconds.",
                    "success": False
                }), 500
            
            # Delete existing files
            for existing_file in existing_files:
                try:
                    existing_file.unlink()
                    print(f"âœ“ Deleted old file: {existing_file.name}")
                except Exception as e:
                    print(f"âœ— Error deleting {existing_file.name}: {e}")
            
            # Wait for file system to stabilize
            time.sleep(1)
        
        uploaded = []
        files_processed = 0
        
        for file in files:
            if files_processed >= MAX_FILES_PER_USER:
                break
                
            if file.filename and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                filepath = user_folder / filename
                
                try:
                    file.save(str(filepath))
                    uploaded.append(filename)
                    files_processed += 1
                    print(f"âœ“ Uploaded: {filename}")
                except Exception as e:
                    print(f"âœ— Error saving {filename}: {e}")
                    return jsonify({
                        "error": f"Failed to save file: {filename}",
                        "success": False
                    }), 500
        
        if len(uploaded) == 0:
            return jsonify({"error": "No valid PDF files uploaded", "success": False}), 400
        
        return jsonify({"success": True, "uploaded": uploaded}), 200
        
    except Exception as e:
        print(f"âœ— Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Upload failed. Please try again.", "success": False}), 500


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
            return jsonify({"error": "Unauthorized", "success": False}), 401
        
        user_folder = get_user_folder(email)
        filepath = user_folder / secure_filename(filename)
        
        if not filepath.exists():
            return jsonify({"error": "File not found", "success": False}), 404
        
        # Delete the file
        try:
            filepath.unlink()
            print(f"âœ“ Deleted file: {filename}")
        except Exception as e:
            print(f"âœ— Error deleting file: {e}")
            return jsonify({"error": "Failed to delete file", "success": False}), 500
        
        # Clear processing status
        if email in user_processing_status:
            del user_processing_status[email]
        
        # Clean up vector DB and registry
        print(f"Cleaning up vector database for {email}...")
        cleanup_success = cleanup_user_data(email, force=True)
        
        if not cleanup_success:
            print(f"âš  Warning: Cleanup partially failed, but file was deleted")
        
        return jsonify({"success": True, "message": "File and associated data deleted"}), 200
        
    except Exception as e:
        print(f"âœ— Delete error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Delete operation failed", "success": False}), 500

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
            "use_reranker": status.get("use_reranker", False),
            "query_enhancement_mode": status.get("query_enhancement_mode", "normal"),
            "message": status.get("message", "")
        }), 200
    except Exception as e:
        print("RAG status error:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/process-document", methods=["POST"])
def process_document():
    email = None
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized", "success": False}), 401
        
        data = request.get_json()
        chunking_method = data.get("chunking_method", "standard")
        hybrid_search = data.get("hybrid_search", False)
        use_reranker = data.get("use_reranker", False)
        query_enhancement_mode = data.get("query_enhancement_mode", "normal")
        
        user_folder = get_user_folder(email)
        pdf_files = list(user_folder.glob("*.pdf"))
        
        if not pdf_files:
            return jsonify({"error": "No PDF file found. Please upload a file first.", "success": False}), 400
        
        # Set processing status
        search_type = "hybrid search" if hybrid_search else "dense search"
        enhancement_text = ""
        if query_enhancement_mode == "expansion":
            enhancement_text = ", query expansion"
        elif query_enhancement_mode == "decomposition":
            enhancement_text = ", query decomposition"
        
        user_processing_status[email] = {
            "status": "processing",
            "chunking_method": chunking_method,
            "hybrid_search": hybrid_search,
            "use_reranker": use_reranker,
            "query_enhancement_mode": query_enhancement_mode,
            "message": f"Processing with {chunking_method} chunking, {search_type}, {'reranking' if use_reranker else 'no reranking'}{enhancement_text}..."
        }
        
        try:
            print(f"\n{'='*60}")
            print(f"Starting document processing for {email}")
            print(f"{'='*60}")
            
            # Clean vector database and registry before processing (with force flag)
            print("Step 1: Cleaning up old vector database...")
            cleanup_success = cleanup_user_data(email, force=True)
            
            if not cleanup_success:
                raise Exception("Failed to cleanup old vector database. Please try again.")
            
            print("âœ“ Cleanup successful")
            time.sleep(2)  # Wait for file system to stabilize
            
            # Create new vector database
            print("Step 2: Creating new vector database...")
            semantic = (chunking_method == "semantic")
            user_vdb = None
            
            try:
                user_vdb = get_user_rag_db(email, semantic=semantic)
                print("âœ“ Vector database created")
                
                # Process the PDF
                print("Step 3: Processing PDF file...")
                pdf_file = pdf_files[0]
                user_vdb.ingest_file_incremental(str(pdf_file))
                print("âœ“ PDF processed successfully")
                
                # Persist the database
                print("Step 4: Persisting vector database...")
                user_vdb.persist()
                print("âœ“ Database persisted")
                
            except Exception as processing_error:
                print(f"âœ— Error during processing: {processing_error}")
                raise processing_error
                
            finally:
                # Always close the database connection
                if user_vdb:
                    try:
                        print("Step 5: Closing database connection...")
                        user_vdb.close()
                        del user_vdb
                        print("âœ“ Database connection closed")
                        time.sleep(1)  # Wait for cleanup
                    except Exception as close_error:
                        print(f"âš  Warning during close: {close_error}")
            
            # Update status to ready
            user_processing_status[email] = {
                "status": "ready",
                "chunking_method": chunking_method,
                "hybrid_search": hybrid_search,
                "use_reranker": use_reranker,
                "query_enhancement_mode": query_enhancement_mode,
                "message": f"Document processed successfully with {chunking_method} chunking, {search_type}, {'reranking' if use_reranker else 'no reranking'}{enhancement_text}"
            }
            
            print(f"\n{'='*60}")
            print(f"âœ“ Processing completed successfully for {email}")
            print(f"{'='*60}\n")
            
            return jsonify({"success": True, "message": "Document processed successfully"}), 200
            
        except Exception as processing_error:
            error_msg = str(processing_error)
            print(f"\n{'='*60}")
            print(f"âœ— Processing failed for {email}")
            print(f"Error: {error_msg}")
            print(f"{'='*60}\n")
            
            # Clean up on error
            print("Cleaning up after error...")
            cleanup_user_data(email, force=True)
            
            # Update status to error
            user_processing_status[email] = {
                "status": "error",
                "chunking_method": chunking_method,
                "hybrid_search": hybrid_search,
                "use_reranker": use_reranker,
                "query_enhancement_mode": query_enhancement_mode,
                "message": f"Processing failed: {error_msg}"
            }
            
            # Return user-friendly error message
            if "readonly database" in error_msg.lower():
                error_response = "Database is locked. Please wait a moment and try again."
            elif "permission" in error_msg.lower():
                error_response = "Permission error. Please try uploading the file again."
            else:
                error_response = "Document processing failed. Please try again."
            
            return jsonify({
                "error": error_response,
                "success": False,
                "details": error_msg if app.debug else None
            }), 500

    except Exception as e:
        print(f"âœ— Process document error: {e}")
        import traceback
        traceback.print_exc()
        
        if email and email in user_processing_status:
            user_processing_status[email]["status"] = "error"
            user_processing_status[email]["message"] = f"Unexpected error: {str(e)}"
        
        return jsonify({
            "error": "Internal server error. Please try again.",
            "success": False,
            "details": str(e) if app.debug else None
        }), 500


@app.route("/query", methods=["POST"])
def query_document():
    email = None
    user_vdb = None
    try:
        email = get_user_from_token(request.headers.get("Authorization"))
        if not email:
            return jsonify({"error": "Unauthorized", "success": False}), 401
        
        # Check if document is processed
        status = user_processing_status.get(email, {})
        if status.get("status") != "ready":
            return jsonify({
                "error": "Document not ready. Please process the document first.",
                "success": False
            }), 400
        
        data = request.get_json()
        question = data.get("question", "").strip()
        query_enhancement_mode = data.get("query_enhancement_mode", status.get("query_enhancement_mode", "normal"))
        
        if not question:
            return jsonify({"error": "Question is required", "success": False}), 400
        
        # Apply query enhancement
        enhanced_query = question
        try:
            if query_enhancement_mode == "expansion":
                from ai.queryenhancements import queryExpansion
                expander = queryExpansion()
                enhanced_query = expander.expand_query(question, llm_instance.llm)
            elif query_enhancement_mode == "decomposition":
                from ai.queryenhancements import queryDecompose
                decomposer = queryDecompose()
                enhanced_query = decomposer.expand_query(question, llm_instance.llm)
        except Exception as enhancement_error:
            print(f"âš  Query enhancement failed: {enhancement_error}, using original query")
            enhanced_query = question
        
        chunking_method = status.get("chunking_method", "standard")
        hybrid_search = status.get("hybrid_search", False)
        use_reranker = status.get("use_reranker", False)
        
        semantic = (chunking_method == "semantic")
        
        try:
            user_vdb = get_user_rag_db(email, semantic=semantic)
            
            retriever = user_vdb.get_retriever(use_hybrid=hybrid_search, k=8 if use_reranker else 4)
            
            # Use enhanced query for retrieval
            retrieved_docs = retriever.invoke(enhanced_query)
            
            # Apply reranking if enabled
            if use_reranker and retrieved_docs:
                try:
                    importlib.reload(ai.reranker)
                    from ai.reranker import Reranker
                    reranker = Reranker(reranker_type=DEFAULT_RERANKER)
                    retrieved_docs = reranker.rerank_docs(enhanced_query, retrieved_docs, top_k=4)
                except Exception as rerank_error:
                    print(f"âš  Reranking failed: {rerank_error}, using non-reranked docs")
            
            # Create custom retriever
            class CustomRetriever:
                def __init__(self, docs):
                    self.docs = docs
                def invoke(self, query):
                    return self.docs
            
            custom_retriever = CustomRetriever(retrieved_docs)
            rag_chain = build_rag_chain(llm_instance, custom_retriever)
            
            # Use enhanced query for answer generation
            result = rag_chain.invoke(enhanced_query)
            
            return jsonify({
                "success": True,
                "answer": result["answer"],
                "context": result["context_text"],
                "source_docs": len(result["context_docs"]),
                "retrieval_method": "Hybrid (Dense + BM25)" if hybrid_search else "Dense Only",
                "chunking_method": chunking_method,
                "reranker_used": use_reranker,
                "reranker_type": DEFAULT_RERANKER if use_reranker else None,
                "query_enhancement_mode": query_enhancement_mode,
                "enhanced_query": enhanced_query if enhanced_query != question else None
            }), 200
            
        finally:
            # Always close the database connection
            if user_vdb:
                try:
                    user_vdb.close()
                    del user_vdb
                except Exception as close_error:
                    print(f"âš  Warning closing database: {close_error}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"âœ— Query error: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Attempt cleanup if database is corrupted
        if "database" in error_msg.lower() and email:
            print(f"Database error detected, attempting cleanup for {email}")
            if email in user_processing_status:
                user_processing_status[email]["status"] = "error"
        
        # Ensure database is closed
        if user_vdb:
            try:
                user_vdb.close()
            except:
                pass
        
        return jsonify({
            "error": "Failed to process query. Please try again or reprocess your document.",
            "success": False,
            "details": error_msg if app.debug else None
        }), 500
    
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