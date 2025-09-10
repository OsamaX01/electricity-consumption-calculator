# IFC Electricity Consumption Calculator

A FastAPI service with web frontend that processes IFC (Industry Foundation Classes) architecture files to calculate electricity consumption using OpenAI API.

## Features

- 🌐 **Web Frontend**: Simple drag-and-drop interface for IFC file uploads
- 📊 **Real-time Analysis**: Instant electricity consumption calculations
- 🏢 **Building Data Extraction**: Comprehensive IFC file parsing
- ⚡ **Energy Calculations**: Lighting, HVAC, and equipment consumption analysis
- 📈 **Visual Results**: Clear consumption breakdowns and building information

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key (optional)
```

3. **Start the application:**
```bash
python start_server.py
```

The application will automatically open in your browser at `http://localhost:8000`

## Alternative Startup Methods

### Method 1: Direct FastAPI
```bash
python main.py
```

### Method 2: Using uvicorn
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

### Web Interface
1. Open `http://localhost:8000` in your browser
2. Drag and drop an IFC file or click to select
3. View the electricity consumption analysis results

### API Endpoints

**Frontend:** `GET /` - Web interface
**Health Check:** `GET /health` - API status
**Calculate:** `POST /calculate-consumption/` - Upload IFC file for analysis
**API Docs:** `GET /docs` - Interactive API documentation

### Example using curl:
```bash
curl -X POST "http://localhost:8000/calculate-consumption/" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_building.ifc"
```

### Example using Python:
```python
python test_client.py
```

## Response Format

```json
{
  "building_data": {
    "spaces": [...],
    "total_floor_area": 1000.0,
    "building_elements": {...},
    "equipment": [...]
  },
  "electricity_consumption": {
    "lighting_consumption": 15000,
    "hvac_consumption": 60000,
    "equipment_consumption": 25000,
    "total_annual_consumption": 100000,
    "energy_intensity": 100,
    "peak_demand": 50,
    "calculation_method": "OpenAI GPT-4 Analysis"
  }
}
```

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Data Extraction from IFC

The service extracts:
- Space areas and volumes
- Building elements (walls, windows)
- Equipment and systems
- Property sets and quantities

## Fallback Calculation

If OpenAI API is unavailable, the service uses standard building energy benchmarks for calculation.
