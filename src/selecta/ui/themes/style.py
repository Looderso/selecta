# src/selecta/ui/themes/style.py
def apply_global_styles(app):
    """Apply global style rules to the application."""
    app.setStyleSheet("""
        QPushButton {
            border-radius: 8px;
            padding: 8px 16px;
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #1f6aa5;
        }
        /* Add more global styles as needed */
    """)
