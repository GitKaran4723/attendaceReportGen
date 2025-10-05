import os
import uuid
import time
from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify, flash
from werkzeug.utils import secure_filename
import pandas as pd
import threading
from datetime import datetime

# Import our attendance processing functions
from script import auto_detect_structure, read_attendance_data, calculate_detailed_statistics, create_detailed_pdf_report

app = Flask(__name__)
app.secret_key = 'attendance_analyzer_secret_key_2025'

# Configuration
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORTS_FOLDER'] = REPORTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store processing status
processing_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_funny_messages():
    """Return a list of funny processing messages"""
    return [
        "🔍 Hunting for absent students like a detective...",
        "🧮 Calculating attendance with quantum precision...",
        "📊 Teaching Excel some manners...",
        "🎯 Tracking down those mysterious attendance patterns...",
        "🔬 Analyzing data like a mad scientist...",
        "📈 Making charts that would make statisticians weep with joy...",
        "🎨 Painting your data beautiful shades of green and red...",
        "🚀 Launching attendance rockets to the moon...",
        "🧙‍♂️ Casting spells on your spreadsheet...",
        "🎪 Juggling numbers like a circus performer...",
        "🍳 Cooking up some spicy attendance insights...",
        "🎵 Making your data dance to the rhythm of analysis...",
        "🔮 Predicting which students need more coffee...",
        "🎭 Turning boring numbers into a dramatic performance...",
        "🏆 Crowning the attendance champions...",
        "🎨 Creating a masterpiece from your messy data...",
        "🧩 Solving the puzzle of student participation...",
        "🎪 Putting on the greatest data show on earth...",
        "🚀 Preparing for PDF launch sequence...",
        "✨ Adding magical finishing touches..."
    ]

def process_attendance_file(file_id, filepath):
    """Process the attendance file in a separate thread"""
    try:
        messages = get_funny_messages()
        
        # Update status with funny messages during processing
        for i, message in enumerate(messages):
            processing_status[file_id] = {
                'status': 'processing',
                'message': message,
                'progress': int((i + 1) / len(messages) * 90)  # Up to 90%
            }
            time.sleep(0.8)  # Dramatic pause for effect
        
        # Actual processing starts here
        processing_status[file_id] = {
            'status': 'processing',
            'message': '🔍 Auto-detecting Excel structure...',
            'progress': 91
        }
        
        header_row, classes_held_row = auto_detect_structure(filepath)
        
        processing_status[file_id] = {
            'status': 'processing',
            'message': '📊 Reading and processing attendance data...',
            'progress': 93
        }
        
        df, classes_held, subject_columns = read_attendance_data(filepath)
        
        processing_status[file_id] = {
            'status': 'processing',
            'message': '🧮 Performing comprehensive statistical analysis...',
            'progress': 95
        }
        
        stats = calculate_detailed_statistics(df, classes_held, subject_columns)
        
        processing_status[file_id] = {
            'status': 'processing',
            'message': '📄 Generating beautiful PDF report...',
            'progress': 97
        }
        
        # Generate unique output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"attendance_report_{timestamp}_{file_id[:8]}.pdf"
        output_path = os.path.join(app.config['REPORTS_FOLDER'], output_filename)
        
        create_detailed_pdf_report(df, classes_held, subject_columns, stats, output_path)
        
        processing_status[file_id] = {
            'status': 'completed',
            'message': '🎉 Report generated successfully!',
            'progress': 100,
            'download_url': f'/download/{output_filename}',
            'stats': {
                'total_students': stats['total_students'],
                'subjects_count': len(subject_columns),
                'avg_attendance': f"{stats['avg_attendance']:.1%}",
                'subjects': subject_columns[:5]  # Show first 5 subjects
            }
        }
        
    except Exception as e:
        processing_status[file_id] = {
            'status': 'error',
            'message': f'❌ Oops! Something went wrong: {str(e)}',
            'progress': 0
        }

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected!')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected!')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        filename = secure_filename(f"{file_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Start processing in background
        processing_thread = threading.Thread(
            target=process_attendance_file,
            args=(file_id, filepath)
        )
        processing_thread.daemon = True
        processing_thread.start()
        
        # Initialize processing status
        processing_status[file_id] = {
            'status': 'starting',
            'message': '🚀 Initializing attendance analyzer...',
            'progress': 0
        }
        
        return redirect(url_for('processing', file_id=file_id))
    else:
        flash('Please upload a valid Excel file (.xlsx or .xls)')
        return redirect(request.url)

@app.route('/processing/<file_id>')
def processing(file_id):
    return render_template('processing.html', file_id=file_id)

@app.route('/status/<file_id>')
def get_status(file_id):
    status = processing_status.get(file_id, {
        'status': 'not_found',
        'message': '❓ File not found',
        'progress': 0
    })
    return jsonify(status)

@app.route('/download/<filename>')
def download_report(filename):
    try:
        filepath = os.path.join(app.config['REPORTS_FOLDER'], filename)
        return send_file(filepath, as_attachment=True, download_name=f"AttendanceReport_{datetime.now().strftime('%Y%m%d')}.pdf")
    except FileNotFoundError:
        flash('File not found!')
        return redirect(url_for('index'))

@app.route('/cleanup/<file_id>')
def cleanup_files(file_id):
    """Clean up uploaded files after processing"""
    try:
        # Remove from processing status
        if file_id in processing_status:
            del processing_status[file_id]
        
        # Clean up uploaded file
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.startswith(file_id):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                break
        
        return jsonify({'status': 'cleaned'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    print("🎉 Starting Attendance Analyzer Web App...")
    print("📊 Ready to process your Excel files!")
    print("🌐 Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)