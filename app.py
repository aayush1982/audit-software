import sqlite3
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import base64
import seaborn as sns


# Constants
DATABASE_NAME = "audit_feedback.db"

PROJECTS = ["Buxar-1", "Buxar-2", "Khurja-1", "Khurja-2", "Ghatampur-1", "Ghatampur-2", "Ghatampur-3"]

CATEGORIES = {
        "1. General": [
            "1.01 Organization chart", 
            "1.02 Communication (Internet, cellular network, server etc)", 
            "1.03 Drawing control",
            "1.04 Safety control",
               
        ],
        "2. 1st column lifting to final tier erection": [
            "2.01 Civil work",
            "2.02 Primary structure",
            "2.03 Grouting work",
            "2.04 Secondary structure(including walkway, staircase,)",
           

        ],
        "3. Assembly of Ceiling Girder Block": [
            "3.01 Ground condition before assembly of ceiling girder block",
            "3.02 Centre line and level checking",
            "3.03 Raising and temporary placement of Girder J (first girder)",
            
               
            ]
         
        #... (Continue with other categories)
    }

RATINGS = ["Excellent", "Good", "Need Improvement", "Work Not Started"]

# Database Functions
def setup_database():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS feedback (
            audit_no INTEGER,
            date TEXT,
            project TEXT,
            category TEXT,
            subcategory TEXT,
            rating TEXT,
            comment TEXT,
            UNIQUE(audit_no, project, category, subcategory)
        )
        """
        conn.execute(create_table_query)
        conn.close()
    except Exception as e:
        st.error(f"An error occurred while setting up the database: {e}")

def insert_or_update_feedback(audit_no, project, category, feedback, comments):
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        current_date = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for subcategory, rating in feedback.items():
            comment = comments.get(subcategory, "")
            cursor.execute("SELECT * FROM feedback WHERE audit_no=? AND project=? AND category=? AND subcategory=?", (audit_no, project, category, subcategory))
            entry = cursor.fetchone()
            
            if entry:
                cursor.execute("UPDATE feedback SET date=?, rating=?, comment=? WHERE audit_no=? AND project=? AND category=? AND subcategory=?", 
                               (current_date, rating, comment, audit_no, project, category, subcategory))
            else:
                cursor.execute("INSERT INTO feedback (audit_no, date, project, category, subcategory, rating, comment) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (audit_no, current_date, project, category, subcategory, rating, comment))
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"An error occurred while saving feedback: {e}")

def export_data(file_format):
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        df = pd.read_sql_query("SELECT * from feedback", conn)
        conn.close()
        
        if file_format == "CSV":
            csv_file = "feedback_data.csv"
            df.to_csv(csv_file, index=False)
            return csv_file
        elif file_format == "Excel":
            excel_file = "feedback_data.xlsx"
            df.to_excel(excel_file, index=False, engine='openpyxl')
            return excel_file
    except Exception as e:
        st.error(f"An error occurred during export: {e}")

def fetch_all_feedback():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feedback")
        data = cursor.fetchall()
        conn.close()
        
        
        columns = ["audit_no", "date", "project", "category", "subcategory", "rating", "comment"]
        df = pd.DataFrame(data, columns=columns)
        return df
    except Exception as e:
        st.error(f"An error occurred while fetching feedback: {e}")

def rating_to_score(rating):
    mapping = {
        "Excellent": 100,
        "Good": 80,
        "Need Improvement": 50,
        "Work Not Started": 0
    }
    return mapping.get(rating, 0)
       
def fetch_feedback_by_audits(audit_nos):
    """Fetch feedback data for a specific list of audit numbers."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Creating a placeholder for each audit number
        placeholders = ', '.join('?' for audit_no in audit_nos)

        query = f"SELECT * FROM feedback WHERE audit_no IN ({placeholders})"
        cursor.execute(query, audit_nos)
        data = cursor.fetchall()
        conn.close()

        columns = ["audit_no", "date", "project", "category", "subcategory", "rating", "comment"]
        df = pd.DataFrame(data, columns=columns)
        return df
    except Exception as e:
        st.error(f"An error occurred while fetching feedback: {e}")


# PDF Report Generation Functions
def generate_pdf_report(audit_no, feedback_data=None):

    if feedback_data is None:
        feedback_data = fetch_feedback_by_audits(audit_no)

    if 'score' not in feedback_data.columns:
        feedback_data['score'] = feedback_data['rating'].apply(rating_to_score)

    if feedback_data.empty:
        st.error("No data found for the selected audit number.")
        return
    
    # Calculate average scores using the updated feedback data
    avg_scores = feedback_data.groupby(['project'])['score'].mean().reset_index()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(200, 220, 255)  # Light blue color
    pdf.set_text_color(50, 50, 50)  # Dark gray color


    logo_path = "lntmhilogo.png"
    pdf.image(logo_path, x=5, y=5, w=40)

    # Enhanced Header
    pdf.set_font("Arial", 'B', size=15)
    pdf.cell(200, 10, txt=f"MPW Audit Report for Audit No: {audit_no}", ln=True, align='C')
    
    pdf.set_font("Arial", 'B', size=10)
    audit_date = feedback_data['date'].iloc[0]
    pdf.cell(200, 10, txt=f"Audit Date: {audit_date}", ln=True, align='C')
    pdf.ln(10)
    

    # Visualization - You need to save your visualization to a temporary image file
    image_path = "temp_plot.png"
    visualize_feedback(audit_no, save_path=image_path)
    pdf.image(image_path, x=25, y=pdf.get_y(), w=150)
    os.remove(image_path)

    # Set the 'y' position after the graph. You may need to adjust the value based on the height of the graph.
    pdf.set_y(pdf.get_y() + 70)  # Here, I'm adding a 70 unit space. You can adjust this value as needed.

    # Enhanced Project Rankings using horizontal bars
    pdf.ln(20)
    pdf.set_font("Arial", 'B', size=8)
    pdf.cell(200, 10, txt="Project Rankings:", ln=True)
    avg_scores = feedback_data.groupby(['project'])['score'].mean().reset_index()
    avg_scores = avg_scores.sort_values(by='score', ascending=True).reset_index(drop=True)
    bar_width = 70
    bar_max_length = 100 # max score

    for _, row in avg_scores.iterrows():
        score = row['score']
        bar_actual_length = (score/bar_max_length) * bar_width
        if score >= 90:
            bar_color = (0, 128, 0)  # Green
        elif 80 <= score < 90:
            bar_color = (144, 238, 144)  # Light Green (#90EE90)
        else:
            bar_color = (255, 0, 0)  # Red

        bar_height = 5
        
        pdf.set_fill_color(*bar_color)
        pdf.cell(60, bar_height, txt=f"{row['project']}:", align='R')  # Adjusted height
        pdf.cell(bar_actual_length, bar_height, border=1, fill=True)  # Adjusted height for the filled bar
        pdf.cell(bar_width - bar_actual_length, bar_height, border=1)  # Adjusted height for the unfilled bar
        pdf.cell(20, bar_height, txt=f"{round(score, 2)}%", align='C')  # Adjusted height for the score
        pdf.ln()

    # Feedback Table
    pdf.ln(20)
    pdf.set_font("Arial", 'B' , size=6)
    pdf.cell(200, 10, txt="Detailed Project evaluation sheet:", ln=True)
    col_widths = [16, 45, 75, 20, 40]
    row_height = 8

    headers = ["Project", "Category", "Subcategory", "Rating", "Comment"]

    # Headers
    pdf.set_fill_color(200, 220, 255)
    for idx, header in enumerate(headers):
        pdf.cell(col_widths[idx], row_height, txt=header, border=1, fill=True)
    pdf.ln()

    # Table Data with alternating row colors
    fill_color = False
    for _, row in feedback_data.iterrows():
        if fill_color:
            pdf.set_fill_color(230, 230, 230)  # Light gray color for alternating row
        for idx, item in enumerate([row['project'], row['category'], row['subcategory'], str(row['rating']), row['comment']]):
            pdf.cell(col_widths[idx], row_height, txt=item, border=1, fill=fill_color)
        fill_color = not fill_color
        pdf.ln()

    # Footer with page number
    pdf.set_y(-15)
    pdf.set_font("Arial", 'I', 6)
    pdf.cell(0, 10, 'Page ' + str(pdf.page_no()), 0, 0, 'C')


    # Saving the PDF
    pdf_output_path = f"audit_report_{audit_no}.pdf"
    pdf.output(pdf_output_path)
    st.write(f"PDF generated: {pdf_output_path}")

    # Return the path of the generated PDF
    return pdf_output_path

def visualize_feedback(audit_no, save_path=None):
    df = fetch_feedback_by_audits(audit_no)
    df['score'] = df['rating'].apply(rating_to_score)

    avg_scores = df.groupby(['project'])['score'].mean().reset_index()
    avg_scores['color'] = avg_scores['score'].apply(lambda x: 'green' if x >= 90 else ('#90EE90' if x >= 80 else 'red'))

    fig, ax = plt.subplots(figsize=(10, 6))
    for _, row in avg_scores.iterrows():
        ax.scatter(row['project'], row['score'], color=row['color'], s=100)

    ax.set_ylabel('Score out of 100')
    ax.set_title(f'Average Score by Project for Audit # {audit_no}')
    ax.set_ylim([0, 110])
    ax.set_yticks(range(0, 110, 10))
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    if save_path:
        plt.savefig(save_path)


def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">{file_label}</a>'
    return href

def pdf_generation():
    st.subheader("PDF Report Generation")
    audit_no_pdf = st.number_input("Enter Audit Number for PDF Report:", min_value=1, step=1)
    if st.button('Generate Report'):
        feedback_data = fetch_feedback_by_audits(audit_no_pdf)
        
        if feedback_data.empty:
            st.error("No data found for the selected audit number.")
        else:
            pdf_path = generate_pdf_report(audit_no_pdf, feedback_data)
            st.success(f"Report generated for Audit No: {audit_no_pdf}")
            st.markdown(get_binary_file_downloader_html(pdf_path, 'Download PDF Report'), unsafe_allow_html=True)

# Data Entry Functions
def data_entry():
    st.subheader("Data Entry")
    audit_no = st.number_input("Enter Audit Number:", min_value=1, step=1)
    selected_project = st.selectbox("Select a Project:", PROJECTS)
    selected_main_category = st.selectbox("Select a Main Category:", list(CATEGORIES.keys()))

    feedback = {}
    comments = {}
    for subcategory in CATEGORIES[selected_main_category]:
        rating = st.radio(subcategory, RATINGS)
        feedback[subcategory] = rating
        comment = st.text_input(f"Comment for {subcategory}:")
        comments[subcategory] = comment

    if st.button("Save Feedback"):
        insert_or_update_feedback(audit_no, selected_project, selected_main_category, feedback, comments)
        st.success(f"Feedback for Audit No {audit_no}, {selected_main_category} in {selected_project} saved successfully!")

    if st.button("Clear Feedback"):
        st.session_state.feedback_cleared = True

# Data Export Functions
def data_export():
    st.subheader("Data Export")
    export_format = st.radio("Select Export Format:", ["CSV", "Excel"])
    if st.button("Export Data"):
        file_name = export_data(export_format)
        st.write(f"Data exported to {file_name}!")

def report_analysis():
    st.sidebar.header('Report Analysis')
    audit_no = st.sidebar.number_input("Enter Audit Number:", min_value=1, value=1, step=1)
    
    if st.sidebar.button("Analyse"):
        try:
            last_three_audits = [audit_no, audit_no-1, audit_no-2]  # Assuming audit numbers are sequential
            df = fetch_feedback_by_audits(last_three_audits)

            if df.empty:
               st.warning(f"No feedback available for audit numbers: {last_three_audits}")
            else:
                # First plot (for selected audit)
                selected_audit_df = df[df['audit_no'] == audit_no]
                selected_audit_df['score'] = selected_audit_df['rating'].apply(rating_to_score)
                avg_scores_selected = selected_audit_df.groupby('project')['score'].mean().reset_index()
                avg_scores_selected['color'] = avg_scores_selected['score'].apply(lambda x: 'green' if x >= 90 else ('#90EE90' if x >= 80 else 'red'))
            
                fig, ax = plt.subplots(figsize=(10, 6))
                for _, row in avg_scores_selected.iterrows():
                     ax.scatter(row['project'], row['score'], color=row['color'], s=100)
                
                ax.set_ylabel('Score out of 100', fontsize=12)
                ax.set_title(f'Average Score by Project for Audit # {audit_no}')
                ax.set_ylim([0, 110])
                ax.set_yticks(range(0, 110, 10))
                ax.grid(True, which='both', linestyle='--', linewidth=0.5)
            
                st.pyplot(fig)
                
                # Group by project and rating, then count the occurrences
                project_rating_counts = (
                    df.groupby(['project', 'rating'])
                    .size()
                    .reset_index(name='count')
                )
                
                # Plotting bar chart
                fig, ax = plt.subplots(figsize=(14, 8))
                sns.barplot(x='project', y='count', hue='rating', data=project_rating_counts, palette='viridis', ax=ax)
                ax.set_title('Project-wise Ratings', fontsize=20)
                ax.set_xlabel('Project', fontsize=20)
                ax.set_ylabel('Number of Ratings', fontsize=20)
                ax.set_xticklabels(ax.get_xticklabels(), fontsize=18)
                plt.legend(title='Rating', title_fontsize='15', fontsize='15')
                plt.tight_layout()
                st.pyplot(fig)

                
                
                
                 # Second plot (for last three audits)
                df['score'] = df['rating'].apply(rating_to_score)
                df['label'] = df.apply(lambda row: f"{row['project']}-{row['audit_no']}", axis=1)
                
                # Preparing data for scatter plot. Grouping by the new label to get the mean score.
                scatter_data = df.groupby('label', as_index=False)['score'].mean()
                
                # Creating the scatter plot
                fig, ax = plt.subplots(figsize=(12, 8))
                ax.scatter(scatter_data['label'], scatter_data['score'], color='b', s=100)
                
                ax.set_ylabel('Score out of 100', fontsize=12)
                ax.set_xlabel('Project-Audit', fontsize=12)
                ax.set_title(f'Average Scores for Last Three Audits by Project')
                ax.set_xticks(range(len(scatter_data['label'])))
                ax.set_xticklabels(scatter_data['label'], rotation=45, ha='right')
                ax.set_yticks(range(0, 110, 10))
                ax.grid(True, which='both', linestyle='--', linewidth=0.5)
                
                st.pyplot(fig)

        except Exception as e:
            st.error(f"An error occurred while generating the report: {e}")


# Main Function
def main():
    setup_database()
    st.title("MPW Site Evaluation App V1.0")

    # Sidebar Navigation
    st.sidebar.title('Navigation')
    sidebar_choice = st.sidebar.radio("Go to", ["Data Entry", "Data Export", "PDF Report Generation", "Report Analysis"])

    if sidebar_choice == "Data Entry":
       data_entry()

    elif sidebar_choice == "Data Export":
       data_export()

    elif sidebar_choice == "PDF Report Generation":
       pdf_generation()

    elif sidebar_choice == "Report Analysis":
       report_analysis()

if __name__ == "__main__":
    main()










