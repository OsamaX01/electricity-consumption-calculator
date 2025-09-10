from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import ifcopenshell
import openai
import os
from typing import Dict, Any
import json
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="IFC Electricity Consumption Calculator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.post("/calculate-consumption/")
async def calculate_electricity_consumption(file: UploadFile = File(...)):
    """
    Process IFC file and calculate electricity consumption using OpenAI API
    """
    if not file.filename.endswith('.ifc'):
        raise HTTPException(status_code=400, detail="File must be an IFC file")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Extract data from IFC file
        ifc_data = extract_ifc_data(temp_file_path)
        
        # Debug: Print extracted data
        print(f"DEBUG - Total spaces: {len(ifc_data['spaces'])}")
        print(f"DEBUG - Total floor area: {ifc_data['total_floor_area']}")
        for i, space in enumerate(ifc_data['spaces'][:3]):  # Show first 3 spaces
            print(f"DEBUG - Space {i}: {space}")
        consumption_result = fallback_calculation(ifc_data)
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return JSONResponse(content={
            "building_data": ifc_data,
            "electricity_consumption": consumption_result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

def extract_ifc_data(file_path: str) -> Dict[str, Any]:
    """Extract relevant data from IFC file for electricity calculation"""
    ifc_file = ifcopenshell.open(file_path)
    
    data = {
        "spaces": [],
        "building_elements": {},
        "equipment": [],
        "total_floor_area": 0,
        "building_envelope": {},
        "building_info": {},
        "hvac_systems": [],
        "lighting_systems": [],
        "electrical_systems": []
    }
    
    # Extract building information
    buildings = ifc_file.by_type("IfcBuilding")
    if buildings:
        building = buildings[0]
        data["building_info"] = {
            "name": getattr(building, 'Name', 'Unknown'),
            "description": getattr(building, 'Description', ''),
            "building_type": getattr(building, 'ObjectType', 'Unknown'),
            "elevation": getattr(building, 'ElevationOfRefHeight', 0)
        }
    
    # Extract spaces with enhanced data
    spaces = ifc_file.by_type("IfcSpace")
    for space in spaces:
        space_data = {
            "name": getattr(space, 'Name', 'Unknown'),
            "area": 0,
            "volume": 0,
            "space_type": getattr(space, 'ObjectType', 'Unknown'),
            "description": getattr(space, 'Description', ''),
            "elevation": 0,
            "properties": {}
        }
        
        # Extract all properties and quantities
        for rel in getattr(space, 'IsDefinedBy', []):
            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                if pset.is_a("IfcPropertySet"):
                    pset_name = getattr(pset, 'Name', 'Unknown')
                    space_data["properties"][pset_name] = {}
                    for prop in pset.HasProperties:
                        prop_name = prop.Name
                        if hasattr(prop, 'NominalValue') and prop.NominalValue:
                            value = prop.NominalValue.wrappedValue
                            space_data["properties"][pset_name][prop_name] = value
                            
                            # Extract key measurements
                            if prop_name in ["NetFloorArea", "GrossFloorArea", "Area"]:
                                space_data["area"] = float(value)
                            elif prop_name in ["NetVolume", "GrossVolume", "Volume"]:
                                space_data["volume"] = float(value)
                            elif prop_name in ["FinishFloorHeight", "Elevation"]:
                                space_data["elevation"] = float(value)
                
                elif pset.is_a("IfcElementQuantity"):
                    for quantity in pset.Quantities:
                        if quantity.is_a("IfcQuantityArea") and quantity.Name in ["NetFloorArea", "GrossFloorArea"]:
                            space_data["area"] = float(quantity.AreaValue)
                        elif quantity.is_a("IfcQuantityVolume") and quantity.Name in ["NetVolume", "GrossVolume"]:
                            space_data["volume"] = float(quantity.VolumeValue)
        
        # Area estimation fallback
        if space_data["area"] == 0:
            if "PARK" in space_data["name"]:
                space_data["area"] = 25.0
            elif space_data["space_type"] in ["OFFICE", "Unknown"]:
                space_data["area"] = 50.0
            else:
                space_data["area"] = 20.0
        
        data["spaces"].append(space_data)
        data["total_floor_area"] += space_data["area"]
    
    # Enhanced building elements extraction
    walls = ifc_file.by_type("IfcWall")
    windows = ifc_file.by_type("IfcWindow")
    doors = ifc_file.by_type("IfcDoor")
    slabs = ifc_file.by_type("IfcSlab")
    roofs = ifc_file.by_type("IfcRoof")
    
    # Calculate wall areas and thermal properties
    total_wall_area = 0
    total_window_area = 0
    
    for wall in walls:
        # Try to get wall area from quantities
        for rel in getattr(wall, 'IsDefinedBy', []):
            if rel.is_a("IfcRelDefinesByProperties"):
                qset = rel.RelatingPropertyDefinition
                if qset.is_a("IfcElementQuantity"):
                    for quantity in qset.Quantities:
                        if quantity.is_a("IfcQuantityArea") and "NetSideArea" in quantity.Name:
                            total_wall_area += float(quantity.AreaValue)
    
    for window in windows:
        # Get window area
        for rel in getattr(window, 'IsDefinedBy', []):
            if rel.is_a("IfcRelDefinesByProperties"):
                qset = rel.RelatingPropertyDefinition
                if qset.is_a("IfcElementQuantity"):
                    for quantity in qset.Quantities:
                        if quantity.is_a("IfcQuantityArea"):
                            total_window_area += float(quantity.AreaValue)
    
    data["building_elements"] = {
        "walls_count": len(walls),
        "windows_count": len(windows),
        "doors_count": len(doors),
        "slabs_count": len(slabs),
        "roofs_count": len(roofs),
        "total_wall_area": total_wall_area,
        "total_window_area": total_window_area,
        "window_to_wall_ratio": total_window_area / total_wall_area if total_wall_area > 0 else 0
    }
    
    # Extract HVAC systems
    hvac_elements = (ifc_file.by_type("IfcAirTerminal") + 
                    ifc_file.by_type("IfcBoiler") + 
                    ifc_file.by_type("IfcChiller") + 
                    ifc_file.by_type("IfcFan") + 
                    ifc_file.by_type("IfcHeatExchanger"))
    
    for hvac in hvac_elements:
        hvac_data = {
            "name": getattr(hvac, 'Name', 'Unknown'),
            "type": hvac.is_a(),
            "properties": {}
        }
        
        # Extract HVAC properties
        for rel in getattr(hvac, 'IsDefinedBy', []):
            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                if pset.is_a("IfcPropertySet"):
                    for prop in pset.HasProperties:
                        if hasattr(prop, 'NominalValue') and prop.NominalValue:
                            hvac_data["properties"][prop.Name] = prop.NominalValue.wrappedValue
        
        data["hvac_systems"].append(hvac_data)
    
    # Extract lighting systems
    lighting_elements = ifc_file.by_type("IfcLightFixture") + ifc_file.by_type("IfcLamp")
    
    for light in lighting_elements:
        light_data = {
            "name": getattr(light, 'Name', 'Unknown'),
            "type": light.is_a(),
            "properties": {}
        }
        
        for rel in getattr(light, 'IsDefinedBy', []):
            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                if pset.is_a("IfcPropertySet"):
                    for prop in pset.HasProperties:
                        if hasattr(prop, 'NominalValue') and prop.NominalValue:
                            light_data["properties"][prop.Name] = prop.NominalValue.wrappedValue
        
        data["lighting_systems"].append(light_data)
    
    # Extract electrical systems
    electrical_elements = (ifc_file.by_type("IfcElectricDistributionBoard") + 
                          ifc_file.by_type("IfcElectricFlowStorageDevice") + 
                          ifc_file.by_type("IfcElectricGenerator") + 
                          ifc_file.by_type("IfcElectricMotor"))
    
    for electrical in electrical_elements:
        elec_data = {
            "name": getattr(electrical, 'Name', 'Unknown'),
            "type": electrical.is_a(),
            "properties": {}
        }
        
        for rel in getattr(electrical, 'IsDefinedBy', []):
            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                if pset.is_a("IfcPropertySet"):
                    for prop in pset.HasProperties:
                        if hasattr(prop, 'NominalValue') and prop.NominalValue:
                            elec_data["properties"][prop.Name] = prop.NominalValue.wrappedValue
        
        data["electrical_systems"].append(elec_data)
    
    # Extract other equipment (existing logic)
    equipment = ifc_file.by_type("IfcFlowTerminal") + ifc_file.by_type("IfcDistributionElement")
    for equip in equipment:
        data["equipment"].append({
            "name": getattr(equip, 'Name', 'Unknown'),
            "type": equip.is_a()
        })
    
    return data

async def calculate_with_openai(ifc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Use OpenAI to calculate electricity consumption based on IFC data"""
    
    print("Preparing OpenAI prompt...")
    prompt = f"""
        You are an energy engineer. Calculate annual electricity consumption for a building using a component-based engineering approach.

        Building data:
        - Total Floor Area: {ifc_data['total_floor_area']} m²
        - Number of Spaces: {len(ifc_data['spaces'])}
        - Building Elements: {ifc_data['building_elements']['walls_count']} walls, {ifc_data['building_elements']['windows_count']} windows

        Assumptions & Calculation Method:
        1. **Lighting**  
        - Use a default Lighting Power Density (LPD) of 8–12 W/m² depending on typical office standards.  
        - Annual lighting energy = Floor area × LPD × 2,000 hours/year ÷ 1000.  

        2. **Equipment (Plug loads)**  
        - Assume equipment load density of 8–15 W/m².  
        - Annual equipment energy = Floor area × equipment density × 2,000 hours/year ÷ 1000.  

        3. **HVAC**  
        - Estimate heating/cooling demand using degree-day approximation for Amman, Jordan (HDD base 18°C ≈ 1500; CDD base 22°C ≈ 900).  
        - Approximate HVAC load = Floor area × 80 kWh/m²·year.  
        - Convert to electricity using system efficiency (COP = 3.0).  

        4. **Totals & Intensity**  
        - Total consumption = lighting + equipment + HVAC.  
        - Energy intensity = Total ÷ Floor area (kWh/m²·year).  

        5. **Recommendations**  
        - Provide 3–5 targeted recommendations for reducing energy use.  
        - Each recommendation must include estimated savings (kWh), cost (JOD), and payback years (<10).  
        - Mention the building type multiple times.  
        - Only suggest practical, cost-effective upgrades (e.g., LED retrofits, improved HVAC efficiency, occupancy sensors).  

        Output Requirements:
        - Respond ONLY in valid JSON.  
        - Keys: lighting_consumption, hvac_consumption, equipment_consumption, total_annual_consumption, energy_intensity, recommendations  
        - Each recommendation object must have: title, description, potential_savings_kwh, implementation_cost_jod, payback_years.  

        Example JSON structure:
        {{
        "lighting_consumption": 0.0,
        "hvac_consumption": 0.0,
        "equipment_consumption": 0.0,
        "total_annual_consumption": 0.0,
        "energy_intensity": 0.0,
        "recommendations": [
            {{
            "title": "LED Lighting Retrofit",
            "description": "Replace existing lighting with LED fixtures tailored for office spaces.",
            "potential_savings_kwh": 0.0,
            "implementation_cost_jod": 0.0,
            "payback_years": 0.0
            }}
        ]
        }}
    """
    
    print("Calling OpenAI API...")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a building energy expert. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    print("Received OpenAI response, parsing...")
    try:
        result = json.loads(response.choices[0].message.content)
        print(f"OpenAI result: {result}")
        return result
    except Exception as e:
        print(f"Failed to parse OpenAI response: {e}")
        return fallback_calculation(ifc_data)

def fallback_calculation(ifc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback electricity calculation if OpenAI API fails"""
    area = ifc_data['total_floor_area']
    
    # If area is still 0, use minimum estimate based on spaces
    if area == 0:
        num_spaces = len(ifc_data['spaces'])
        if num_spaces > 0:
            area = num_spaces * 30.0  # 30 m² per space minimum
        else:
            area = 100.0  # Default minimum building area
    
    print(f"DEBUG - Using area for calculation: {area} m²")
    
    # Standard building energy intensities (kWh/m²/year)
    lighting = area * 15  # 15 kWh/m²/year
    hvac = area * 60      # 60 kWh/m²/year  
    equipment = area * 25 # 25 kWh/m²/year
    total = lighting + hvac + equipment
    
    # Default recommendations for fallback
    recommendations = [
        {
            "title": "LED Lighting Upgrade",
            "description": "Replace existing lighting with LED fixtures",
            "potential_savings_kwh": lighting * 0.3,
            "implementation_cost_jod": area * 15,
            "payback_years": 3
        },
        {
            "title": "Smart Thermostat Installation",
            "description": "Install programmable thermostats for HVAC optimization",
            "potential_savings_kwh": hvac * 0.15,
            "implementation_cost_jod": 500,
            "payback_years": 2
        },
        {
            "title": "Building Insulation Improvement",
            "description": "Enhance wall and roof insulation",
            "potential_savings_kwh": hvac * 0.2,
            "implementation_cost_jod": area * 25,
            "payback_years": 5
        }
    ]
    
    return {
        "lighting_consumption": lighting,
        "hvac_consumption": hvac,
        "equipment_consumption": equipment,
        "total_annual_consumption": total,
        "energy_intensity": total / area if area > 0 else 0,
        "peak_demand": total / 2000,  # Rough estimate
        "calculation_method": "Standard Building Energy Benchmarks",
        "recommendations": recommendations
    }

@app.get("/")
async def root():
    """Serve the frontend HTML file"""
    return FileResponse("index.html")

@app.post("/analyze-ifc")
async def analyze_ifc(file: UploadFile = File(...)):
    """
    Process IFC file and calculate electricity consumption
    """
    if not file.filename.endswith('.ifc'):
        raise HTTPException(status_code=400, detail="File must be an IFC file")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Extract data from IFC file
        print(f"Extracting data from IFC file: {file.filename}")
        ifc_data = extract_ifc_data(temp_file_path)
        print(f"Extracted building data - Area: {ifc_data['total_floor_area']} m², Spaces: {len(ifc_data['spaces'])}")
        
        # Calculate consumption using OpenAI
        try:
            print("Attempting OpenAI calculation...")
            consumption_result = await calculate_with_openai(ifc_data)
            print("OpenAI calculation successful")
        except Exception as e:
            print(f"OpenAI failed: {e}, using fallback")
            consumption_result = fallback_calculation(ifc_data)
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        # Format response for frontend
        return {
            "annual_usage_kwh": consumption_result["total_annual_consumption"],
            "estimated_cost": consumption_result["total_annual_consumption"] * 0.12,  # JOD 0.12 per kWh
            "recommendations": consumption_result.get("recommendations", []),
            "assumptions": [
                f"Building area: {ifc_data['total_floor_area']:.1f} m²",
                f"Lighting: 15 kWh/m²/year",
                f"HVAC: 60 kWh/m²/year", 
                f"Equipment: 25 kWh/m²/year",
                f"Energy intensity: {consumption_result['energy_intensity']:.1f} kWh/m²/year"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/health")
async def health():
    return {"message": "IFC Electricity Consumption Calculator API", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
