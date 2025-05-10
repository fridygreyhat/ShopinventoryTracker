from app import app  # noqa: F401

if __name__ == "__main__":
    # Start the Flask development server
    # Listen on all interfaces (0.0.0.0) and port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
