# Deployment and Integration Guide

This document highlights that the **QueryMind** system is now ready for production deployment and supports multi-user scalability.

## 🚀 Readiness for Deployment

The system is built on a modern, containerized stack:
- **Backend**: FastAPI (Python 3.10+)
- **Database**: SQLite (Metadata) & ChromaDB (Vector Search)
- **Deployment**: Docker Compose for easy orchestration.

### Steps to Deploy
1. **Configure Environment**: Update the `.env` file with your production URL and LLM API keys.
2. **Launch Services**:
   ```bash
   docker-compose up -d --build
   ```
3. **Database Migration**: The system automatically initializes the SQLite database on startup.

---

## 👥 Multi-User Testing & Scalability

We have moved beyond a single "Admin" setup. The system now supports multiple independent users (Vendors/Clients).

### How to Test with Various Users
1. **Register New Users**:
   Use the `POST /admin/register` endpoint to create unique users.
   ```json
   { "username": "vendor_a", "password": "password123" }
   ```
2. **Independent Configuration**:
   Each user logs in to get their own JWT token. They can then:
   - Connect their own SQL database.
   - Upload their own PDF/Document files.
3. **Data Isolation**:
   The system automatically isolates data using `tenant_id = f"user_{user_id}"`. Vendor A cannot see or search Vendor B's data.

---

## 🤖 Chatbot Integration Guide

You can now use QueryMind as a chatbot in any web application by embedding the provided widget.

### 1. The Widget File
The integration file is located at [chat_widget.html](file:///c:/Users/HP/hp/DocumentsN/FlairMinds/chatbot1/querymind/widget/chat_widget.html).

### 2. Configuration for Different Applications
To use the chatbot for a specific user/vendor in their respective web application, modify the script block in the widget:

```javascript
const API_URL = "https://your-deployed-api.com";
const USER_ID = 2; // Set this to the ID of the specific vendor/user
```

### 3. Embedding the Chatbot
Copy the HTML, CSS, and JS from `chat_widget.html` into your web application's footer. The widget will:
- Display the chat icon.
- Targeted the specific knowledge base of `USER_ID`.
- Provide AI-powered answers based strictly on that user's data.

### 4. Scalability Verification
To verify scalability, embed two widgets on two different pages with different `USER_ID`s. Ask questions about data specific to each user and verify that they only receive answers related to their own data.
