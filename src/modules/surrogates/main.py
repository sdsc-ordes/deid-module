from generator import generate_surrogates
from loader import load_input, load_surrogate_map, load_name_database, save_output, save_surrogate_map

from fastapi import FastAPI

app = FastAPI(title="Surrogate Generator")
@app.post("/pii")
async def root():
    return {"message": "POST PIIs to get surrogates."}

def main(input_file, output_file, surrogate_map_path=None):
    input = load_input(input_file)
    
    if input is not None:
        surrogate_map = load_surrogate_map(surrogate_map_path)
        name_db = load_name_database()
        output, surrogate_map = generate_surrogates(input, surrogate_map, name_db)
        save_output(output, output_file)
        surrogate_map.save(surrogate_map_path) 


if __name__ == "__main__":
    main()
