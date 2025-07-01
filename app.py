from flask import Flask, request, send_file, render_template
import pandas as pd
from io import BytesIO

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        file_a = request.files.get('file_a')
        file_b = request.files.get('file_b')
        primary_key = request.form.get('primary_key')
        secondary_keys = request.form.getlist('secondary_keys')

        if not file_a or not file_b or not primary_key:
            return "Missing files or key column.", 400

        try:
            df_a = pd.read_excel(BytesIO(file_a.read()))
            df_b = pd.read_excel(BytesIO(file_b.read()))

            name_a = file_a.filename
            name_b = file_b.filename

            # Ensure primary key exists
            if primary_key not in df_a.columns or primary_key not in df_b.columns:
                return f"Primary key '{primary_key}' missing in one of the files", 400

            # Merge on primary key
            merged = df_a.merge(df_b, on=primary_key, how='outer', indicator=True)

            reconciled = merged[merged['_merge'] == 'both'].drop(columns='_merge')
            file_a_only = merged[merged['_merge'] == 'left_only'].drop(columns='_merge')
            file_b_only = merged[merged['_merge'] == 'right_only'].drop(columns='_merge')

            # Summary sheet
            summary_data = {
                "Metric": [
                    "File A",
                    "File B",
                    "Matched Rows",
                    "Unmatched in File A",
                    "Unmatched in File B"
                ],
                "Value": [
                    name_a,
                    name_b,
                    len(reconciled),
                    len(file_a_only),
                    len(file_b_only)
                ]
            }
            summary_df = pd.DataFrame(summary_data)

            # Generate Excel report
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                def write_sheet(df, sheet_name):
                    metadata = pd.DataFrame({"Metadata": [
                        f"Primary Key: {primary_key}",
                        f"Secondary Keys: {', '.join(secondary_keys) if secondary_keys else 'None'}",
                        f"File A: {name_a}",
                        f"File B: {name_b}"
                    ]})
                    metadata.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                    df.to_excel(writer, sheet_name=sheet_name, startrow=4, index=False)

                write_sheet(reconciled, 'Reconciled')
                write_sheet(file_a_only, 'FileA_Only')
                write_sheet(file_b_only, 'FileB_Only')

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                download_name='reconciliation_report.xlsx',
                as_attachment=True
            )

        except Exception as e:
            return f"Error processing files: {str(e)}", 500

    sample_columns = ['TransactionID', 'Date', 'Amount', 'Description']
    return render_template('index.html', columns=sample_columns)
