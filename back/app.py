from flask import Flask, request, send_file
import xml.etree.ElementTree as ET
import pandas as pd
from flask_cors import CORS
import csv
import io

app = Flask(__name__)
CORS(app)
def parse_kml(kml_file):
    tree = ET.parse(kml_file)
    root = tree.getroot()
    
    namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    wifi_data = []
    for placemark in root.findall('.//kml:Placemark', namespaces):
        name_elem = placemark.find('kml:name', namespaces)
        name = name_elem.text if name_elem is not None else 'Unknown'
        
        description_elem = placemark.find('kml:description', namespaces)
        description = description_elem.text if description_elem is not None else 'No Description'
        
        coordinates_elem = placemark.find('.//kml:coordinates', namespaces)
        coordinates = coordinates_elem.text.strip() if coordinates_elem is not None else '0,0'
        
        description_lines = description.splitlines()
        
        signal_line = next((line for line in description_lines if 'Signal' in line), None)
        signal = int(signal_line.split(': ')[1]) if signal_line else None
        
        network_id_line = next((line for line in description_lines if 'Network ID' in line), None)
        network_id = network_id_line.split(': ')[1] if network_id_line else None
        
        frequency_line = next((line for line in description_lines if 'Frequency' in line), None)
        frequency = frequency_line.split(': ')[1] if frequency_line else None
        
        coords = coordinates.split(',')
        lon = float(coords[0]) if len(coords) > 0 else None
        lat = float(coords[1]) if len(coords) > 1 else None
        
        wifi_data.append({
            'name': name,
            'network_id': network_id,
            'signal': signal,
            'frequency': frequency,
            'longitude': lon,
            'latitude': lat
        })
    
    return pd.DataFrame(wifi_data)

def merge_data(file1_data, file2_data):
    merged_data = {}
    for row1 in file1_data:
        ssid = row1[0]
        for row2 in file2_data:
            if ssid == row2[0]:
                merged_row = row1[0:8] + row2[0:]
                signal = int(row2[2])
                
                if ssid not in merged_data or signal > merged_data[ssid][1]:
                    merged_data[ssid] = (merged_row, signal)
                break
    
    return [row for row, _ in merged_data.values()]

@app.route('/process', methods=['POST'])
def process_files():
    kml_file = request.files['kmlFile']
    csv_file = request.files['csvFile']
    
    # Process KML file
    df_kml = parse_kml(kml_file)
    
    # Process CSV file
    csv_data = list(csv.reader(io.StringIO(csv_file.read().decode('utf-8'))))
    csv_headers = csv_data[0]
    csv_data = csv_data[1:]
    
    # Merge data
    merged_headers = csv_headers[0:8] + df_kml.columns.tolist()
    merged_data = merge_data(csv_data, df_kml.values.tolist())
    
    # Create output CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(merged_headers)
    writer.writerows(merged_data)
    
    # Prepare the response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='merged_output.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)