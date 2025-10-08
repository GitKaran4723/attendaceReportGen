import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
import re

# Configuration
CONFIG = {
    'attendance_threshold': 0.75,  # 75% attendance threshold
    'page_size': A4,
    'report_title': 'Attendance Report',
    'font_sizes': {
        'title': 18,
        'heading': 14,
        'subheading': 12,
        'normal': 10,
        'small': 8
    }
}

def auto_detect_structure(file_path):
    """
    Auto-detect the structure of the Excel file to handle different formats
    """
    # Read the entire Excel file to analyze structure
    df_full = pd.read_excel(file_path, header=None)
    
    # Find the row with column headers (usually contains "Student", "Name", "Reg", etc.)
    header_row = None
    classes_held_row = None
    
    for idx, row in df_full.iterrows():
        row_str = ' '.join([str(cell).lower() for cell in row if pd.notna(cell)])
        
        # Look for header indicators
        if any(keyword in row_str for keyword in ['student', 'name', 'reg', 'sl', 'percentage']):
            header_row = idx
            break
    
    # Look for "classes held" row (usually right after headers)
    if header_row is not None:
        for idx in range(header_row + 1, min(header_row + 5, len(df_full))):
            row_str = ' '.join([str(cell).lower() for cell in df_full.iloc[idx] if pd.notna(cell)])
            if 'classes' in row_str or 'held' in row_str or any(str(cell).isdigit() for cell in df_full.iloc[idx] if pd.notna(cell)):
                classes_held_row = idx
                break
    
    return header_row, classes_held_row

def read_attendance_data(file_path):
    """
    Read attendance data from Excel file with auto-detection of structure
    """
    # Auto-detect structure
    header_row, classes_held_row = auto_detect_structure(file_path)
    
    if header_row is None:
        # Fallback to original method
        header_row = 3
        classes_held_row = 4
    
    # Read the Excel file with detected header row
    df = pd.read_excel(file_path, header=header_row)
    
    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]
    
    # Try to standardize column names (order matters - check specific patterns first)
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        # Check for registration number first (more specific)
        if any(keyword in col_lower for keyword in ['reg', 'registration', 'roll']):
            column_mapping[col] = 'Reg_No'
        # Then check for serial/sl number (avoid conflicts)
        elif any(keyword in col_lower for keyword in ['sl', 'serial']) and 'reg' not in col_lower:
            column_mapping[col] = 'Sl_No'
        # Student name
        elif any(keyword in col_lower for keyword in ['student', 'name']) and 'reg' not in col_lower:
            column_mapping[col] = 'Student_Name'
        # Percentage/total
        elif any(keyword in col_lower for keyword in ['percentage', 'total', 'overall']):
            column_mapping[col] = 'Percentage'
    
    # Apply column mapping
    df = df.rename(columns=column_mapping)
    
    # Get classes held information
    classes_held = {}
    if classes_held_row is not None:
        classes_row = pd.read_excel(file_path, header=header_row).iloc[classes_held_row - header_row - 1]
        
        for col in df.columns:
            if col not in ['Sl_No', 'Reg_No', 'Student_Name', 'Percentage'] and pd.notna(classes_row.get(col, None)):
                try:
                    # Convert to string first to handle any format
                    val_str = str(classes_row[col]).strip()
                    # Remove percentage sign if present
                    val_str = val_str.replace('%', '')
                    classes_held[col] = int(float(val_str))
                except (ValueError, TypeError):
                    classes_held[col] = 0
    
    # Remove classes held row and other non-student rows
    df_clean = df.copy()
    if classes_held_row is not None and classes_held_row - header_row - 1 >= 0:
        df_clean = df_clean.drop(classes_held_row - header_row - 1, errors='ignore')
    
    # Remove rows without student names
    df_clean = df_clean.dropna(subset=['Student_Name']).reset_index(drop=True)
    
    # Identify subject columns (numeric columns that aren't ID columns)
    subject_columns = []
    for col in df_clean.columns:
        if col not in ['Sl_No', 'Reg_No', 'Student_Name', 'Percentage']:
            # Check if column contains mostly numeric data
            try:
                pd.to_numeric(df_clean[col], errors='coerce')
                subject_columns.append(col)
            except:
                pass
    
    # Helper function to clean and convert values (handles percentages)
    def clean_numeric_value(val):
        """Convert value to numeric, handling percentages and empty values"""
        if pd.isna(val) or val == '' or str(val).strip() == '':
            return np.nan
        try:
            # Convert to string and clean
            val_str = str(val).strip()
            # Check if it's a percentage format
            if '%' in val_str:
                # Remove % and convert to decimal (e.g., "75%" -> 75.0)
                return float(val_str.replace('%', ''))
            else:
                # Just convert to float
                return float(val_str)
        except (ValueError, TypeError):
            return np.nan
    
    # Convert numeric columns, handling percentages and empty values
    for col in subject_columns + ['Percentage']:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(clean_numeric_value)
    
    return df_clean, classes_held, subject_columns

def calculate_detailed_statistics(df, classes_held, subject_columns):
    """
    Calculate comprehensive statistics including subject-wise analysis for each student
    """
    stats = {}
    threshold = CONFIG['attendance_threshold']
    
    # Overall statistics
    stats['total_students'] = len(df)
    
    # Handle overall percentage - check if values need to be converted
    percentage_column_exists = 'Percentage' in df.columns
    percentage_has_data = False
    
    if percentage_column_exists:
        # Check if the percentage column has any valid data
        valid_pct_count = df['Percentage'].notna().sum()
        percentage_has_data = valid_pct_count > 0
        
        if percentage_has_data:
            max_pct = df['Percentage'].max()
            
            # Only check format if we have valid, non-zero data
            if pd.notna(max_pct) and max_pct > 0:
                stats['percentage_calculated'] = False  # Using provided data
                if max_pct <= 1.0:
                    # Values are in decimal form (e.g., 0.75), no conversion needed
                    stats['avg_attendance'] = df['Percentage'].mean()
                    stats['highest_attendance'] = df['Percentage'].max()
                    stats['lowest_attendance'] = df['Percentage'].min()
                    threshold_compare = threshold
                else:
                    # Values are in percentage form (e.g., 75), convert for display
                    stats['avg_attendance'] = df['Percentage'].mean() / 100 if pd.notna(df['Percentage'].mean()) else 0
                    stats['highest_attendance'] = df['Percentage'].max() / 100 if pd.notna(df['Percentage'].max()) else 0
                    stats['lowest_attendance'] = df['Percentage'].min() / 100 if pd.notna(df['Percentage'].min()) else 0
                    threshold_compare = threshold * 100
            else:
                # All zeros or NaN - treat as no data
                percentage_has_data = False
    
    # If percentage column is empty or doesn't exist, calculate from subject data
    if not percentage_has_data:
        print("   ℹ️  Overall percentage column is empty or missing - calculating from subject data...")
        
        # Calculate overall percentage for each student from their subject attendance
        calculated_percentages = []
        for _, row in df.iterrows():
            total_attended = 0
            total_classes = 0
            
            for subject in subject_columns:
                if subject in row and pd.notna(row[subject]):
                    attended = row[subject]
                    classes = classes_held.get(subject, 0)
                    
                    if classes > 0:
                        try:
                            total_attended += float(attended)
                            total_classes += classes
                        except (ValueError, TypeError):
                            pass
            
            if total_classes > 0:
                calculated_percentages.append(total_attended / total_classes)
            else:
                calculated_percentages.append(0)
        
        if calculated_percentages and any(p > 0 for p in calculated_percentages):
            # Add calculated percentage to DataFrame
            df['Percentage'] = calculated_percentages
            
            stats['avg_attendance'] = sum(calculated_percentages) / len(calculated_percentages)
            stats['highest_attendance'] = max(calculated_percentages)
            stats['lowest_attendance'] = min(calculated_percentages)
            threshold_compare = threshold
            percentage_has_data = True
            stats['percentage_calculated'] = True  # Flag to indicate calculation
            print(f"   ✅ Calculated overall percentages (Avg: {stats['avg_attendance']:.1%})")
        else:
            # No data available at all
            stats['avg_attendance'] = 0
            stats['highest_attendance'] = 0
            stats['lowest_attendance'] = 0
            threshold_compare = threshold
            stats['percentage_calculated'] = False
            print("   ⚠️  No attendance data available to calculate percentages")
    
    # Students with attendance >= threshold
    if percentage_has_data and 'Percentage' in df.columns:
        # Filter out NaN values before comparison
        valid_percentages = df['Percentage'].dropna()
        if len(valid_percentages) > 0:
            stats['students_above_threshold'] = len(valid_percentages[valid_percentages >= threshold_compare])
            stats['students_below_threshold'] = len(valid_percentages[valid_percentages < threshold_compare])
        else:
            stats['students_above_threshold'] = 0
            stats['students_below_threshold'] = stats['total_students']
    else:
        stats['students_above_threshold'] = 0
        stats['students_below_threshold'] = stats['total_students']
    
    # Subject-wise statistics
    stats['subject_averages'] = {}
    stats['subject_attendance_rates'] = {}
    
    for subject in subject_columns:
        if subject in df.columns:
            # Calculate mean, ignoring NaN values
            subject_mean = df[subject].mean()
            
            # Check if the subject has any valid data
            if pd.notna(subject_mean):
                stats['subject_averages'][subject] = subject_mean
                
                # Calculate attendance rate if classes held info available
                if subject in classes_held and classes_held[subject] > 0:
                    stats['subject_attendance_rates'][subject] = (subject_mean / classes_held[subject]) * 100
                else:
                    # If no classes held info, assume the values are already percentages
                    stats['subject_attendance_rates'][subject] = subject_mean
            else:
                # No data for this subject
                stats['subject_averages'][subject] = 0
                stats['subject_attendance_rates'][subject] = 0
    
    # Individual student analysis
    stats['student_details'] = []
    
    for _, row in df.iterrows():
        # Handle registration number properly
        reg_value = row.get('Reg_No', None)
        if pd.isna(reg_value) or reg_value == '' or str(reg_value).strip() == '':
            reg_no = None  # Don't show if empty or NaN
        else:
            reg_no = str(reg_value).strip()
        
        # Handle overall percentage
        overall_pct_value = row.get('Percentage', None)
        if pd.isna(overall_pct_value) or overall_pct_value == 0:
            # Calculate from subject data if percentage is missing or zero
            total_attended = 0
            total_classes = 0
            
            for subject in subject_columns:
                if subject in row and pd.notna(row[subject]):
                    attended = row[subject]
                    classes = classes_held.get(subject, 0)
                    
                    if classes > 0:
                        try:
                            total_attended += float(attended)
                            total_classes += classes
                        except (ValueError, TypeError):
                            pass
            
            if total_classes > 0:
                overall_pct = total_attended / total_classes
            else:
                overall_pct = 0
        else:
            # Check if it's in decimal or percentage format
            overall_pct = float(overall_pct_value)
            if overall_pct > 1.0:
                overall_pct = overall_pct / 100  # Convert to decimal
        
        student_info = {
            'name': row.get('Student_Name', 'Unknown'),
            'reg_no': reg_no,
            'overall_percentage': overall_pct,
            'subjects': {},
            'subjects_below_threshold': [],
            'strengths': [],
            'needs_attention': []
        }
        
        # Subject-wise analysis for each student
        for subject in subject_columns:
            if subject in row and pd.notna(row[subject]):
                attended = row[subject]
                total_classes = classes_held.get(subject, 0)
                
                # Determine if the value is already a percentage or raw attendance
                if total_classes > 0:
                    # We have classes held info, so calculate percentage
                    try:
                        attended_int = int(float(attended))
                        percentage = (attended_int / total_classes) * 100
                        student_info['subjects'][subject] = {
                            'attended': attended_int,
                            'total': total_classes,
                            'percentage': percentage,
                            'status': 'Good' if percentage >= threshold * 100 else 'Needs Attention'
                        }
                    except (ValueError, TypeError):
                        # Skip if can't convert to int
                        continue
                else:
                    # No classes held info - assume the value is already a percentage
                    try:
                        percentage = float(attended)
                        student_info['subjects'][subject] = {
                            'attended': 'N/A',
                            'total': 'N/A',
                            'percentage': percentage,
                            'status': 'Good' if percentage >= threshold * 100 else 'Needs Attention'
                        }
                    except (ValueError, TypeError):
                        # Skip if can't convert to float
                        continue
                
                # Add to tracking lists
                if subject in student_info['subjects']:
                    percentage = student_info['subjects'][subject]['percentage']
                    if percentage < threshold * 100:
                        student_info['subjects_below_threshold'].append(subject)
                        student_info['needs_attention'].append(f"{subject}: {percentage:.1f}%")
                    else:
                        student_info['strengths'].append(f"{subject}: {percentage:.1f}%")
        
        stats['student_details'].append(student_info)
    
    # Subject-wise performance ranking
    stats['subject_rankings'] = {}
    for subject in subject_columns:
        if subject in df.columns:
            subject_data = df[['Student_Name', subject]].copy()
            subject_data = subject_data.dropna()
            subject_data = subject_data.sort_values(subject, ascending=False)
            stats['subject_rankings'][subject] = subject_data.head(5).to_dict('records')
    
    return stats

def create_detailed_pdf_report(df, classes_held, subject_columns, stats, output_file='attendance_report_detailed.pdf'):
    """
    Create a comprehensive PDF report with detailed subject-wise analysis
    """
    doc = SimpleDocTemplate(output_file, pagesize=CONFIG['page_size'], 
                           rightMargin=50, leftMargin=50, 
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=CONFIG['font_sizes']['title'],
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=CONFIG['font_sizes']['heading'],
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=CONFIG['font_sizes']['subheading'],
        spaceAfter=8,
        textColor=colors.darkgreen
    )
    
    # Auto-detect institution and course info from Excel or use defaults
    institution_info = "DETAILED ATTENDANCE ANALYSIS REPORT"
    try:
        # Try to extract info from first few rows of original Excel
        df_full = pd.read_excel(output_file.replace('_detailed.pdf', '.xlsx') if '.xlsx' not in output_file else 'exampleAtt.xlsx', header=None, nrows=5)
        for _, row in df_full.iterrows():
            row_text = ' '.join([str(cell) for cell in row if pd.notna(cell)])
            if len(row_text) > 20 and any(word in row_text.upper() for word in ['UNIVERSITY', 'COLLEGE', 'DEPARTMENT']):
                institution_info = row_text
                break
    except:
        pass
    
    # Title
    title = Paragraph(f"{institution_info}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Report Generation Info
    report_info_text = f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>"
    report_info_text += f"<b>Analysis Threshold:</b> {CONFIG['attendance_threshold']*100:.0f}%"
    
    # Add note if overall percentage was calculated
    if stats.get('percentage_calculated', False):
        report_info_text += "<br/><b>Note:</b> Overall percentages calculated from subject-wise attendance (no percentage column in source data)"
    
    report_info = Paragraph(report_info_text, styles['Normal'])
    elements.append(report_info)
    elements.append(Spacer(1, 20))
    
    # Executive Summary
    elements.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    
    threshold_pct = CONFIG['attendance_threshold'] * 100
    summary_data = [
        ['Metric', 'Value'],
        ['Total Students Analyzed', str(stats['total_students'])],
        ['Overall Average Attendance', f"{stats['avg_attendance']:.1%}"],
        ['Highest Individual Attendance', f"{stats['highest_attendance']:.1%}"],
        ['Lowest Individual Attendance', f"{stats['lowest_attendance']:.1%}"],
        [f'Students with ≥{threshold_pct:.0f}% Attendance', f"{stats['students_above_threshold']} ({stats['students_above_threshold']/stats['total_students']:.1%})"],
        [f'Students Needing Attention (<{threshold_pct:.0f}%)', f"{stats['students_below_threshold']} ({stats['students_below_threshold']/stats['total_students']:.1%})"],
        ['Number of Subjects Analyzed', str(len(subject_columns))]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Classes Held Information
    elements.append(Paragraph("CLASSES HELD", heading_style))
    
    classes_data = [['Subject', 'Classes Held']]
    for subject in subject_columns:
        subject_name = subject.replace('_', ' ').title()
        count = classes_held.get(subject, 0)
        # Show N/A if no classes held information available
        classes_str = str(count) if count > 0 else 'N/A (Percentage format)'
        classes_data.append([subject_name, classes_str])
    
    classes_table = Table(classes_data, colWidths=[2.5*inch, 1.5*inch])
    classes_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(classes_table)
    elements.append(Spacer(1, 20))
    
    # Subject-wise Performance Analysis
    elements.append(Paragraph("SUBJECT-WISE PERFORMANCE ANALYSIS", heading_style))
    
    subject_avg_data = [['Subject', 'Avg Classes\nAttended', 'Total Classes\nHeld', 'Attendance\nRate', 'Performance\nStatus']]
    
    for subject in subject_columns:
        if subject in stats['subject_averages']:
            avg_attended = stats['subject_averages'][subject]
            classes = classes_held.get(subject, 0)
            attendance_rate = stats['subject_attendance_rates'].get(subject, 0)
            
            # Skip subjects with no data
            if avg_attended == 0 and attendance_rate == 0:
                continue
            
            # Determine performance status
            if attendance_rate >= threshold_pct:
                status = "Excellent"
            elif attendance_rate >= threshold_pct * 0.8:
                status = "Good"
            elif attendance_rate > 0:
                status = "Needs Focus"
            else:
                status = "No Data"
            
            subject_name = subject.replace('_', ' ').title()
            subject_avg_data.append([
                subject_name,
                f"{avg_attended:.1f}" if avg_attended > 0 else 'N/A',
                str(classes) if classes > 0 else 'N/A',
                f"{attendance_rate:.1f}%" if attendance_rate > 0 else 'N/A',
                status
            ])
    
    subject_avg_table = Table(subject_avg_data, colWidths=[1.8*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    subject_avg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightcyan),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    
    elements.append(subject_avg_table)
    elements.append(PageBreak())
    
    # Individual Student Analysis
    elements.append(Paragraph("DETAILED STUDENT-WISE ANALYSIS", heading_style))
    
    # Create detailed student tables
    students_per_page = 6
    student_count = 0
    
    for student_info in stats['student_details']:
        if student_count > 0 and student_count % students_per_page == 0:
            elements.append(PageBreak())
        
        # Student header
        student_name = student_info['name']
        reg_no = student_info.get('reg_no', None)
        overall_pct = student_info.get('overall_percentage', 0)
        
        # Create header text based on whether registration number exists
        if reg_no and reg_no != 'N/A':
            header_text = f"<b>{student_name}</b> (Reg: {reg_no}) - Overall: {overall_pct:.1%}"
        else:
            header_text = f"<b>{student_name}</b> - Overall: {overall_pct:.1%}"
        
        student_header = Paragraph(
            header_text,
            subheading_style
        )
        elements.append(student_header)
        
        # Subject-wise breakdown for this student
        if student_info['subjects']:
            student_subject_data = [['Subject', 'Attended', 'Total', 'Percentage', 'Status']]
            
            for subject, subject_data in student_info['subjects'].items():
                subject_name = subject.replace('_', ' ').title()
                status = subject_data['status']
                
                # Handle N/A values properly
                attended_str = str(subject_data['attended']) if subject_data['attended'] != 'N/A' else 'N/A'
                total_str = str(subject_data['total']) if subject_data['total'] != 'N/A' else 'N/A'
                
                student_subject_data.append([
                    subject_name,
                    attended_str,
                    total_str,
                    f"{subject_data['percentage']:.1f}%",
                    status
                ])
            
            student_table = Table(student_subject_data, colWidths=[1.5*inch, 0.8*inch, 0.8*inch, 1*inch, 1.2*inch])
            
            # Style the student table
            student_table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]
            
            # Color code based on performance
            for i, (subject, subject_data) in enumerate(student_info['subjects'].items(), 1):
                if subject_data['percentage'] < CONFIG['attendance_threshold'] * 100:
                    student_table_style.append(('BACKGROUND', (0, i), (-1, i), colors.lightpink))
                else:
                    student_table_style.append(('BACKGROUND', (0, i), (-1, i), colors.lightgreen))
            
            student_table.setStyle(TableStyle(student_table_style))
            elements.append(student_table)
            
            # Add insights for this student
            insights = []
            if student_info['strengths']:
                insights.append(f"<b>Strengths:</b> {', '.join(student_info['strengths'][:3])}")
            if student_info['needs_attention']:
                insights.append(f"<b>Needs Attention:</b> {', '.join(student_info['needs_attention'])}")
            
            if insights:
                insight_para = Paragraph("<br/>".join(insights), styles['Normal'])
                elements.append(insight_para)
        
        elements.append(Spacer(1, 12))
        student_count += 1
    
    # Add comprehensive notes and legend
    elements.append(PageBreak())
    elements.append(Paragraph("REPORT LEGEND & NOTES", heading_style))
    
    legend_text = f"""<b>Color Coding:</b><br/>
    • <b>Green highlighting:</b> Subject attendance ≥ {CONFIG['attendance_threshold']*100:.0f}% (Meeting requirements)<br/>
    • <b>Pink highlighting:</b> Subject attendance < {CONFIG['attendance_threshold']*100:.0f}% (Needs attention)<br/><br/>
    <b>Performance Status:</b><br/>
    • <b>Excellent:</b> ≥{CONFIG['attendance_threshold']*100:.0f}% attendance<br/>
    • <b>Good:</b> ≥{CONFIG['attendance_threshold']*80:.0f}% attendance<br/>
    • <b>Needs Focus:</b> <{CONFIG['attendance_threshold']*80:.0f}% attendance<br/><br/>
    <b>Important Notes:</b><br/>
    • Overall attendance is calculated based on all subjects combined<br/>
    • Students requiring immediate attention are those with multiple subjects below threshold<br/>
    • This report was generated automatically and should be reviewed by academic staff<br/>
    • Individual subject-wise analysis helps identify specific areas of concern for each student"""
    
    note = Paragraph(legend_text, styles['Normal'])
    elements.append(note)
    
    # Build PDF
    doc.build(elements)
    print(f"✅ Comprehensive PDF report generated: {output_file}")

def main():
    """
    Enhanced main function for comprehensive attendance report generation
    """
    try:
        # Configuration
        excel_file = 'exampleAtt.xlsx'
        pdf_output = 'attendance_report_detailed.pdf'
        
        print("🔍 Auto-detecting Excel file structure...")
        header_row, classes_held_row = auto_detect_structure(excel_file)
        print(f"   • Header row detected at: {header_row}")
        print(f"   • Classes held row detected at: {classes_held_row}")
        
        print("📊 Reading and processing attendance data...")
        df, classes_held, subject_columns = read_attendance_data(excel_file)
        print(f"   • Students found: {len(df)}")
        print(f"   • Subjects detected: {len(subject_columns)} ({', '.join(subject_columns)})")
        
        print("🧮 Performing comprehensive statistical analysis...")
        stats = calculate_detailed_statistics(df, classes_held, subject_columns)
        
        print("📄 Generating detailed PDF report with subject-wise analysis...")
        create_detailed_pdf_report(df, classes_held, subject_columns, stats, pdf_output)
        
        # Enhanced reporting
        print(f"\n✅ REPORT GENERATION COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"📊 SUMMARY STATISTICS:")
        print(f"   • Total students analyzed: {stats['total_students']}")
        print(f"   • Subjects analyzed: {len(subject_columns)}")
        print(f"   • Average attendance: {stats['avg_attendance']:.1%}")
        print(f"   • Attendance range: {stats['lowest_attendance']:.1%} - {stats['highest_attendance']:.1%}")
        
        threshold_pct = CONFIG['attendance_threshold'] * 100
        print(f"\n📈 PERFORMANCE BREAKDOWN:")
        print(f"   • Students meeting {threshold_pct:.0f}% threshold: {stats['students_above_threshold']} ({stats['students_above_threshold']/stats['total_students']:.1%})")
        print(f"   • Students needing attention: {stats['students_below_threshold']} ({stats['students_below_threshold']/stats['total_students']:.1%})")
        
        print(f"\n📚 SUBJECT-WISE PERFORMANCE:")
        for subject in subject_columns:
            if subject in stats['subject_attendance_rates']:
                rate = stats['subject_attendance_rates'][subject]
                avg = stats['subject_averages'][subject]
                total = classes_held.get(subject, 0)
                
                # Skip subjects with no data
                if avg == 0 and rate == 0:
                    continue
                
                # Determine status icon
                if rate >= threshold_pct:
                    status = "✅"
                elif rate >= threshold_pct * 0.8:
                    status = "⚠️"
                elif rate > 0:
                    status = "❌"
                else:
                    status = "ℹ️"
                
                # Format output based on whether we have total classes
                if total > 0:
                    print(f"   {status} {subject.replace('_', ' ').title()}: {rate:.1f}% (Avg: {avg:.1f}/{total})")
                else:
                    print(f"   {status} {subject.replace('_', ' ').title()}: {rate:.1f}%")
        
        print(f"\n📄 OUTPUT:")
        print(f"   • Detailed PDF report: {pdf_output}")
        print(f"   • Report includes individual student subject-wise breakdowns")
        print(f"   • Color-coded performance indicators included")
        print(f"   • Ready for academic review and action planning")
        
        # Identify students needing immediate attention
        critical_students = [s for s in stats['student_details'] if len(s['subjects_below_threshold']) >= 2]
        if critical_students:
            print(f"\n⚠️  STUDENTS REQUIRING IMMEDIATE ATTENTION:")
            for student in critical_students[:5]:  # Show top 5
                subjects_list = ', '.join(student['subjects_below_threshold'])
                print(f"   • {student['name']}: Multiple subjects below threshold ({subjects_list})")
        
    except FileNotFoundError:
        print(f"❌ Error: Excel file '{excel_file}' not found in current directory!")
        print("Please ensure the Excel file exists and try again.")
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Ensure Excel file has proper attendance data structure")
        print("2. Check that student names and numeric attendance data are present")
        print("3. Verify file is not corrupted or password-protected")
        import traceback
        print(f"\nDetailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    main()