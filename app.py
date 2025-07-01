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

        if not file_a or not file_b:
            return "Please upload both files.", 400

        try:
            # Read files into memory
            df_a = pd.read_excel(BytesIO(file_a.read()))
            df_b = pd.read_excel(BytesIO(file_b.read()))

            name_a = file_a.filename
            name_b = file_b.filename

            # Ensure primary key exists in both DataFrames
            if primary_key not in df_a.columns or primary_key not in df_b.columns:
                return f"Primary key '{primary_key}' missing in one of the files", 400

            # Merge using primary key
            merged = df_a.merge(df_b, on=primary_key, how='outer', indicator=True)

            reconciled = merged[merged['_merge'] == 'both'].drop(columns='_merge')
            file_a_only = merged[merged['_merge'] == 'left_only'].drop(columns='_merge')
            file_b_only = merged[merged['_merge'] == 'right_only'].drop(columns='_merge')

            # Summary sheet
            summary_data = {
                "Metric": [
                    "Total Rows in File A",
                    "Total Rows in File B",
                    "Matched Rows",
                    "Unmatched in File A",
                    "Unmatched in File B"
                ],
                "Count": [
                    len(df_a),
                    len(df_b),
                    len(reconciled),
                    len(file_a_only),
                    len(file_b_only)
                ]
            }
            summary_df = pd.DataFrame(summary_data)

            # Metadata
            metadata = pd.DataFrame({
                "Metadata": [
                    f"File A: {name_a}",
                    f"File B: {name_b}",
                    f"Primary Key: {primary_key}",
                    f"Secondary Keys: {', '.join(secondary_keys) if secondary_keys else 'None'}"
                ]
            })

            # Generate Excel report
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                metadata.to_excel(writer, sheet_name='Reconciled', index=False, header=False)
                reconciled.to_excel(writer, sheet_name='Reconciled', startrow=4, index=False)

                metadata.to_excel(writer, sheet_name='FileA_Only', index=False, header=False)
                file_a_only.to_excel(writer, sheet_name='FileA_Only', startrow=4, index=False)

                metadata.to_excel(writer, sheet_name='FileB_Only', index=False, header=False)
                file_b_only.to_excel(writer, sheet_name='FileB_Only', startrow=4, index=False)

                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            output.seek(0)

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                download_name='reconciliation_report.xlsx',
                as_attachment=True
            )

        except Exception as e:
            return f"Error processing files: {str(e)}", 500

    # GET request — show form
    try:
        # Mock column list (will be replaced dynamically in real use)
        columns = ['TransactionID', 'Date', 'Amount', 'Description']
    except Exception:
        columns = []

    return render_template('index.html', columns=columns)

if __name__ == '__main__':
    app.run(debug=False)
