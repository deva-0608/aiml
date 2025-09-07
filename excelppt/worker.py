import os, json
# from presentation import create_ppt  # your external logic

def generate_ppt(uuid):
    upload_dir = f"storage/uploads/{uuid}"
    output_dir = f"storage/outputs/{uuid}"
    os.makedirs(output_dir, exist_ok=True)

    input_json_path = os.path.join(upload_dir, "input.json")
    with open(input_json_path) as f:
        config = json.load(f)

    input_csv = next((f for f in os.listdir(upload_dir) if f.startswith("input") and f.endswith(".csv")), None)
    if not input_csv:
        return

    input_csv_path = os.path.join(upload_dir, input_csv)
    input_pptx_path = os.path.join(upload_dir, config.get("input_pptx")) if config.get("input_pptx") else None
    output_ppt_path = os.path.join(output_dir, "presentation.pptx")


    print(input_csv_path,input_pptx_path)
    # create_ppt(
    #     csv_path=input_csv_path,
    #     columns=config.get("important_columns", []),
    #     theme=config.get("theme", "Default"),
    #     template_path=input_pptx_path,
    #     output_path=output_ppt_path,
    #     preview_dir=output_dir
    # )