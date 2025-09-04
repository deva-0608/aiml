import pandas as pd
import numpy as np
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Import your analyzer (assuming it's in a separate file or included above)
# from excel_json_analyzer import ExcelToJSONAnalyzer

class ExcelToJSONAnalyzer:
    def __init__(self):
        self.df = None
        self.file_path = None
        self.analysis_results = {}

    def read_file(self, file_path):
        """Read CSV or XLSX files directly from file path"""
        self.file_path = file_path
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == '.csv':
                self.df = pd.read_csv(file_path)
                print(f"✅ Successfully loaded CSV file with {len(self.df)} rows and {len(self.df.columns)} columns")
            elif file_extension in ['.xlsx', '.xls']:
                self.df = pd.read_excel(file_path)
                print(f"✅ Successfully loaded Excel file with {len(self.df)} rows and {len(self.df.columns)} columns")
            else:
                raise ValueError("Unsupported file format. Please use CSV or Excel files.")

            return True
        except Exception as e:
            print(f"❌ Error reading file: {str(e)}")
            return False

    def separate_data_types(self):
        """Separate data into categorical, numerical, and datetime columns"""
        if self.df is None:
            return None, None, None

        # Numerical columns
        numerical_columns = list(self.df.select_dtypes(include=[np.number]).columns)
        
        # Categorical columns
        categorical_columns = list(self.df.select_dtypes(include=['object', 'category']).columns)
        
        # DateTime columns
        datetime_columns = list(self.df.select_dtypes(include=['datetime64']).columns)
        
        # Try to detect datetime columns from object columns
        potential_datetime_cols = []
        for col in categorical_columns.copy():
            try:
                # Try to convert first few non-null values to datetime
                sample_data = self.df[col].dropna().head(10)
                if len(sample_data) > 0:
                    pd.to_datetime(sample_data, errors='raise')
                    potential_datetime_cols.append(col)
                    categorical_columns.remove(col)
            except:
                continue
        
        datetime_columns.extend(potential_datetime_cols)
        
        return (
            tuple(numerical_columns),
            tuple(categorical_columns), 
            tuple(datetime_columns)
        )

    def analyze_dataset(self):
        """Comprehensive data analysis for JSON output"""
        if self.df is None:
            return None

        analysis = {}

        # Get data type separation
        numerical_cols, categorical_cols, datetime_cols = self.separate_data_types()

        # Basic dataset information
        analysis['basic_info'] = {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'file_name': os.path.basename(self.file_path) if self.file_path else "Unknown",
            'columns': list(self.df.columns)
        }

        # Data types analysis
        analysis['data_types'] = {
            'numerical_columns': list(numerical_cols),
            'categorical_columns': list(categorical_cols),
            'datetime_columns': list(datetime_cols)
        }

        # Missing values analysis
        missing_data = self.df.isnull().sum()
        missing_percentages = (missing_data / len(self.df)) * 100

        analysis['missing_values'] = {
            'total_missing': int(missing_data.sum()),
            'columns_with_missing': {k: int(v) for k, v in missing_data[missing_data > 0].to_dict().items()},
            'missing_percentages': {k: float(v) for k, v in missing_percentages[missing_percentages > 0].to_dict().items()}
        }

        # Statistical summary for numerical columns
        if analysis['data_types']['numerical_columns']:
            numerical_summary = self.df[analysis['data_types']['numerical_columns']].describe()
            # Convert to serializable format
            analysis['numerical_summary'] = {
                col: {stat: float(val) for stat, val in numerical_summary[col].to_dict().items()}
                for col in numerical_summary.columns
            }

        # Categorical data insights
        categorical_insights = {}
        for col in analysis['data_types']['categorical_columns']:
            unique_values = self.df[col].nunique()
            most_common = self.df[col].value_counts().head(3).to_dict()
            categorical_insights[col] = {
                'unique_values': int(unique_values),
                'most_common_values': {k: int(v) for k, v in most_common.items()}
            }
        analysis['categorical_insights'] = categorical_insights

        # Data quality assessment
        duplicate_rows = self.df.duplicated().sum()
        analysis['data_quality'] = {
            'duplicate_rows': int(duplicate_rows),
            'completeness_score': float(((len(self.df) * len(self.df.columns) - missing_data.sum()) / 
                                       (len(self.df) * len(self.df.columns))) * 100)
        }

        self.analysis_results = analysis
        return analysis

    def generate_left_column_content(self):
        """Generate content for left division"""
        if not self.analysis_results:
            return "No analysis available"

        analysis = self.analysis_results
        content = []

        # Dataset Overview
        content.append("• Dataset Overview")
        content.append(f"  - {analysis['basic_info']['total_rows']:,} total records")
        content.append(f"  - {analysis['basic_info']['total_columns']} feature variables")
        content.append(f"  - {len(analysis['data_types']['numerical_columns'])} numerical fields")
        content.append(f"  - {len(analysis['data_types']['categorical_columns'])} categorical fields")
        content.append("")

        # Data Quality
        content.append("• Data Quality Assessment")
        completeness = analysis['data_quality']['completeness_score']
        content.append(f"  - Overall completeness: {completeness:.1f}%")

        if analysis['data_quality']['duplicate_rows'] > 0:
            content.append(f"  - Duplicate records: {analysis['data_quality']['duplicate_rows']}")
        else:
            content.append(f"  - No duplicate records detected")

        quality_rating = "Excellent" if completeness > 95 else "Good" if completeness > 85 else "Fair" if completeness > 70 else "Poor"
        content.append(f"  - Data quality rating: {quality_rating}")
        content.append("")

        # Missing Data Impact
        content.append("• Missing Data Impact")
        if analysis['missing_values']['total_missing'] > 0:
            missing_cols = analysis['missing_values']['columns_with_missing']
            content.append(f"  - {len(missing_cols)} columns affected")
            content.append(f"  - {analysis['missing_values']['total_missing']:,} missing values total")

            # Show top 2 columns with missing data
            sorted_missing = sorted(missing_cols.items(), key=lambda x: x[1], reverse=True)[:2]
            for col, missing_count in sorted_missing:
                percentage = analysis['missing_values']['missing_percentages'][col]
                content.append(f"  - {col}: {percentage:.1f}% missing")
        else:
            content.append("  - No missing values detected")
            content.append("  - Complete data integrity maintained")

        return "\n".join(content)

    def generate_right_column_content(self):
        """Generate content for right division"""
        if not self.analysis_results:
            return "No analysis available"

        analysis = self.analysis_results
        content = []

        # Analytical Capabilities
        content.append("• Analytical Capabilities")
        numerical_cols = len(analysis['data_types']['numerical_columns'])
        categorical_cols = len(analysis['data_types']['categorical_columns'])

        if numerical_cols > 0:
            content.append(f"  - Statistical analysis ready")
            content.append(f"  - Trend and correlation studies")
            content.append(f"  - Predictive modeling potential")

        if categorical_cols > 0:
            content.append(f"  - Segmentation analysis available")
            content.append(f"  - Classification studies possible")

        if numerical_cols > 0 and categorical_cols > 0:
            content.append(f"  - Mixed-type analysis supported")

        content.append("")

        # Business Value
        content.append("• Business Value Indicators")

        # Data volume assessment
        data_volume = analysis['basic_info']['total_rows']
        if data_volume > 10000:
            content.append("  - Large-scale dataset for enterprise insights")
        elif data_volume > 1000:
            content.append("  - Medium-scale dataset for departmental analysis")
        else:
            content.append("  - Focused dataset for targeted analysis")

        # Variable richness
        var_count = analysis['basic_info']['total_columns']
        if var_count > 20:
            content.append("  - Rich feature set for comprehensive analysis")
        elif var_count > 10:
            content.append("  - Adequate variables for detailed insights")
        else:
            content.append("  - Focused variable set for specific analysis")

        # Data quality business impact
        completeness = analysis['data_quality']['completeness_score']
        if completeness > 90:
            content.append("  - High reliability for business decisions")
        elif completeness > 75:
            content.append("  - Moderate reliability with some limitations")
        else:
            content.append("  - Requires data cleaning for optimal use")

        content.append("")

        # Key Applications
        content.append("• Key Applications")

        # Determine applications based on data characteristics
        file_name = analysis['basic_info']['file_name'].lower()
        columns = [col.lower() for col in analysis['basic_info']['columns']]

        if any(keyword in file_name or any(keyword in col for col in columns) 
               for keyword in ['sales', 'revenue', 'price', 'cost']):
            content.append("  - Sales performance analysis")
            content.append("  - Revenue optimization studies")
            content.append("  - Pricing strategy development")
        elif any(keyword in file_name or any(keyword in col for col in columns) 
                 for keyword in ['customer', 'client', 'user']):
            content.append("  - Customer behavior analysis")
            content.append("  - Market segmentation studies")
            content.append("  - Customer lifetime value modeling")
        elif any(keyword in file_name or any(keyword in col for col in columns) 
                 for keyword in ['employee', 'staff', 'hr', 'payroll']):
            content.append("  - Workforce analytics")
            content.append("  - Performance management insights")
            content.append("  - HR optimization strategies")
        else:
            content.append("  - Exploratory data analysis")
            content.append("  - Pattern recognition studies")
            content.append("  - Statistical modeling projects")
            content.append("  - Business intelligence reporting")

        return "\n".join(content)

    def generate_json_analysis(self):
        """Create JSON output with analysis (similar to slide 2 format)"""
        if self.df is None or not self.analysis_results:
            return {"error": "No data available for analysis"}

        analysis = self.analysis_results
        completeness = analysis['data_quality']['completeness_score']

        # Create JSON structure similar to the slide format
        json_output = {
            "main_title": "Dataset Overview & Analysis",
            "summary_stats": {
                "total_records": analysis['basic_info']['total_rows'],
                "total_variables": analysis['basic_info']['total_columns'],
                "completeness_percentage": round(completeness, 1)
            },
            "": {
                "content": self.generate_left_column_content(),
                "structured_data": {
                    "dataset_overview": {
                        "total_records": analysis['basic_info']['total_rows'],
                        "feature_variables": analysis['basic_info']['total_columns'],
                        "numerical_fields": len(analysis['data_types']['numerical_columns']),
                        "categorical_fields": len(analysis['data_types']['categorical_columns'])
                    },
                    "data_quality": {
                        "completeness_percentage": round(completeness, 1),
                        "duplicate_rows": analysis['data_quality']['duplicate_rows'],
                        "quality_rating": "Excellent" if completeness > 95 else "Good" if completeness > 85 else "Fair" if completeness > 70 else "Poor"
                    },
                    "missing_data": {
                        "total_missing": analysis['missing_values']['total_missing'],
                        "columns_affected": len(analysis['missing_values']['columns_with_missing']),
                        "columns_with_missing": analysis['missing_values']['columns_with_missing']
                    }
                }
            },
            "": {
                "content": self.generate_right_column_content(),
                "structured_data": {
                    "analytical_capabilities": {
                        "statistical_analysis": len(analysis['data_types']['numerical_columns']) > 0,
                        "segmentation_analysis": len(analysis['data_types']['categorical_columns']) > 0,
                        "mixed_type_analysis": len(analysis['data_types']['numerical_columns']) > 0 and len(analysis['data_types']['categorical_columns']) > 0
                    },
                    "business_value": {
                        "data_scale": "Large-scale" if analysis['basic_info']['total_rows'] > 10000 else "Medium-scale" if analysis['basic_info']['total_rows'] > 1000 else "Focused",
                        "variable_richness": "Rich" if analysis['basic_info']['total_columns'] > 20 else "Adequate" if analysis['basic_info']['total_columns'] > 10 else "Focused",
                        "reliability": "High" if completeness > 90 else "Moderate" if completeness > 75 else "Limited"
                    }
                }
            },
            "data_type_separation": {
                "numerical_columns": analysis['data_types']['numerical_columns'],
                "categorical_columns": analysis['data_types']['categorical_columns'],
                "datetime_columns": analysis['data_types']['datetime_columns']
            },
            "full_analysis": analysis,
            "generation_timestamp": datetime.now().isoformat(),
            "processing_info": {
                "job_id": getattr(self, 'job_id', None),
                "file_path": self.file_path,
                "processing_status": "completed"
            }
        }

        return json_output

    def process_file_for_worker(self, file_path, job_id=None):
        """Process file specifically for worker loop"""
        self.job_id = job_id  # Store job_id for reference
        
        print(f"🚀 Starting analysis for job {job_id}...")
        
        # Read file
        if not self.read_file(file_path):
            return {"error": "Failed to read file", "job_id": job_id}
        
        # Analyze dataset
        self.analyze_dataset()
        
        # Generate JSON analysis
        return self.generate_json_analysis()

# Define your paths
UPLOADS_DIR = Path("uploads")
OUTPUTS_DIR = Path("outputs")

def process_csv_file(job_id, input_file):
    """Process CSV file using the ExcelToJSONAnalyzer"""
    try:
        # Initialize analyzer
        analyzer = ExcelToJSONAnalyzer()
        
        # Process the file
        json_result = analyzer.process_file_for_worker(input_file, job_id)
        
        # Get data type separation tuples
        numerical_cols, categorical_cols, datetime_cols = analyzer.separate_data_types()
        
        # Add data type tuples to the result
        json_result["data_type_tuples"] = {
            "numerical": numerical_cols,
            "categorical": categorical_cols,
            "datetime": datetime_cols
        }
        
        return json_result, True
        
    except Exception as e:
        error_result = {
            "error": f"Processing failed: {str(e)}",
            "job_id": job_id,
            "file_path": input_file,
            "processing_status": "failed",
            "generation_timestamp": datetime.now().isoformat()
        }
        return error_result, False


def worker_loop(poll_interval=5):
    """Modified worker loop using ExcelToJSONAnalyzer"""
    print("Worker started. Watching for uploads...")
    
    # Ensure directories exist
    UPLOADS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    
    while True:
        try:
            for job_dir in UPLOADS_DIR.glob("*"):
                job_id = job_dir.name
                out_dir = OUTPUTS_DIR / job_id
                out_dir.mkdir(parents=True, exist_ok=True)   # ensure output folder exists
                
                json_path = out_dir / "report.json"
                status_path = out_dir / "status.txt"
                
                # Skip if already processed
                if json_path.exists() and status_path.exists():
                    continue
                
                # Look for CSV files (you can extend to include xlsx, xls)
                files = list(job_dir.glob("*.csv"))
                if not files:
                    # Also check for Excel files
                    files = list(job_dir.glob("*.xlsx")) + list(job_dir.glob("*.xls"))
                
                if not files:
                    continue

                input_file = str(files[0])
                print(f"Processing {input_file}...")

                # Write processing status
                with open(status_path, "w") as f:
                    f.write("processing")

                # Process the file using ExcelToJSONAnalyzer
                json_result, success = process_csv_file(job_id, input_file)

                # Save JSON result
                with open(json_path, "w") as f:
                    json.dump(json_result, f, indent=2, default=str)

                # Update status
                with open(status_path, "w") as f:
                    f.write("completed" if success else "failed")

                if success:
                    print(f"✅ Analysis completed successfully:")
                    print(f"   JSON -> {json_path}")
                    print(f"   Records: {json_result.get('summary_stats', {}).get('total_records', 'N/A')}")
                    print(f"   Variables: {json_result.get('summary_stats', {}).get('total_variables', 'N/A')}")
                    print(f"   Completeness: {json_result.get('summary_stats', {}).get('completeness_percentage', 'N/A')}%")
                else:
                    print(f"❌ Analysis failed:")
                    print(f"   Error: {json_result.get('error', 'Unknown error')}")
                    print(f"   JSON -> {json_path}")
                
        except Exception as e:
            print(f"❌ Worker loop error: {str(e)}")
            
        time.sleep(poll_interval)

def test_single_file(file_path, job_id="test_job"):
    """Test function to process a single file"""
    json_result, success = process_csv_file(job_id, file_path)
    
    if success:
        print("✅ Test completed successfully!")
        print(json.dumps(json_result, indent=2))
        
        # Save JSON to a file
        output_file = Path("outputs") / f"{job_id}_report.json"
        output_file.parent.mkdir(exist_ok=True)  # create folder if not exists
        with open(output_file, "w") as f:
            json.dump(json_result, f, indent=2, default=str)
        print(f"✅ JSON saved to {output_file}")
        
        # Print data type tuples
        tuples_data = json_result.get("data_type_tuples", {})
        print(f"\n📊 Data Type Separation:")
        print(f"Numerical: {tuples_data.get('numerical', ())}")
        print(f"Categorical: {tuples_data.get('categorical', ())}")
        print(f"DateTime: {tuples_data.get('datetime', ())}")
    else:
        print("❌ Test failed!")
        print(json_result.get('error', 'Unknown error'))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode - process a single file
        if len(sys.argv) > 2:
            test_single_file(sys.argv[2])
        else:
            print("Usage: python worker.py test <file_path>")
    else:
        # Normal worker mode
        worker_loop()
        
        