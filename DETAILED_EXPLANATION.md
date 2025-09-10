# IFC Electricity Consumption Calculator - Detailed Technical Explanation

## Overview

This FastAPI service processes Industry Foundation Classes (IFC) architecture files to calculate building electricity consumption using advanced data extraction and energy modeling techniques. The system combines geometric analysis, building systems identification, and energy calculation algorithms to provide accurate consumption estimates.

## Architecture & Components

### 1. FastAPI Web Service (`main.py`)
- **Endpoint**: `POST /calculate-consumption/`
- **Input**: IFC file upload (multipart/form-data)
- **Output**: JSON response with building data and electricity consumption analysis
- **Error Handling**: Comprehensive exception handling with HTTP status codes
- **File Processing**: Temporary file management for secure IFC processing

### 2. IFC Data Extraction Engine

#### Core Libraries
- **ifcopenshell**: Industry-standard IFC file parser and processor
- **Supports**: IFC2x3, IFC4, IFC4x1 schemas
- **Capabilities**: Geometric analysis, property extraction, relationship traversal

#### Data Extraction Categories

##### A. Building Information
```python
building_info = {
    "name": "Building Name",
    "description": "Building Description", 
    "building_type": "Office/Residential/Industrial",
    "elevation": "Reference height in meters"
}
```

##### B. Space Analysis
```python
space_data = {
    "name": "Space identifier",
    "area": "Floor area in m²",
    "volume": "Space volume in m³",
    "space_type": "Functional classification",
    "elevation": "Floor level height",
    "properties": {
        "Pset_SpaceCommon": {
            "Reference": "Space reference code",
            "IsExternal": "Boolean external/internal"
        },
        "Pset_SpaceOccupancyRequirements": {
            "OccupancyType": "Building code classification",
            "OccupancyNumber": "Maximum occupant count"
        }
    }
}
```

##### C. Building Envelope Analysis
```python
building_elements = {
    "walls_count": "Number of wall elements",
    "windows_count": "Number of window elements", 
    "doors_count": "Number of door elements",
    "slabs_count": "Number of slab elements",
    "roofs_count": "Number of roof elements",
    "total_wall_area": "Calculated wall area in m²",
    "total_window_area": "Calculated window area in m²",
    "window_to_wall_ratio": "Thermal performance indicator"
}
```

##### D. Building Systems Detection
- **HVAC Systems**: Air terminals, boilers, chillers, fans, heat exchangers
- **Lighting Systems**: Light fixtures, lamps with specifications
- **Electrical Systems**: Distribution boards, generators, motors
- **Equipment**: Waste terminals, distribution elements

## Mathematical Energy Calculation Framework

### 1. Energy Intensity Standards (kWh/m²/year)

Based on international building energy benchmarks:

| System | Intensity | Application |
|--------|-----------|-------------|
| Lighting | 15 kWh/m²/year | General illumination |
| HVAC | 60 kWh/m²/year | Heating, cooling, ventilation |
| Equipment | 25 kWh/m²/year | Plug loads, appliances |
| **Total** | **100 kWh/m²/year** | **Typical office building** |

### 2. Space-Specific Calculations

#### Parking Facilities (Current Example)
- **Lighting**: Reduced to 5-10 kWh/m²/year (minimal lighting requirements)
- **HVAC**: Reduced to 20-30 kWh/m²/year (ventilation only, no heating/cooling)
- **Equipment**: Minimal 5 kWh/m²/year (security, access control)

#### Office Buildings
- **Lighting**: 15-20 kWh/m²/year (task lighting, ambient lighting)
- **HVAC**: 60-80 kWh/m²/year (full climate control)
- **Equipment**: 25-35 kWh/m²/year (computers, printers, appliances)

### 3. Peak Demand Calculation
```
Peak Demand (kW) = Total Annual Consumption (kWh) / 2000 hours
```
Assumes 2000 operating hours per year (typical commercial building)

### 4. Energy Intensity Calculation
```
Energy Intensity = Total Annual Consumption / Total Floor Area
```

## IFC Property Set Analysis

### Standard Property Sets Extracted

#### Pset_SpaceCommon
- **Reference**: Space identification code
- **IsExternal**: Thermal boundary classification
- **GrossPlannedArea**: Design area
- **NetPlannedArea**: Usable area

#### Pset_SpaceOccupancyRequirements  
- **OccupancyType**: Building code classification (e.g., '0121-98-03' for parking)
- **OccupancyNumber**: Maximum occupant load
- **OccupancyNumberPeak**: Peak occupancy

#### Pset_SpaceHeaterTypeCommon
- **Reference**: Heating system reference
- **HeatTransferSurfaceArea**: Heat exchange area
- **NominalCapacity**: Heating capacity

### Quantity Sets (QTO)
- **Qto_SpaceBaseQuantities**: Areas, volumes, perimeters
- **Qto_WallBaseQuantities**: Wall areas, lengths, heights
- **Qto_WindowBaseQuantities**: Window areas, perimeters

## Building Systems Integration

### 1. HVAC System Detection
```python
hvac_elements = [
    "IfcAirTerminal",      # Air diffusers, grilles
    "IfcBoiler",           # Heating boilers
    "IfcChiller",          # Cooling chillers  
    "IfcFan",              # Ventilation fans
    "IfcHeatExchanger"     # Heat recovery units
]
```

### 2. Lighting System Analysis
```python
lighting_elements = [
    "IfcLightFixture",     # Light fixtures
    "IfcLamp"              # Individual lamps
]
```

### 3. Electrical System Mapping
```python
electrical_elements = [
    "IfcElectricDistributionBoard",  # Electrical panels
    "IfcElectricGenerator",          # Backup generators
    "IfcElectricMotor"               # Motor loads
]
```

## Advanced Calculation Features

### 1. Thermal Envelope Analysis
- **Wall Area Calculation**: Extracted from IFC geometry
- **Window-to-Wall Ratio**: Thermal performance indicator
- **Heat Loss Calculation**: Based on envelope areas and thermal properties

### 2. Space Type Recognition
- **Automatic Classification**: Based on IFC space names and properties
- **Energy Adjustment**: Different intensities per space type
- **Occupancy Integration**: Load calculations based on occupant density

### 3. Equipment Load Analysis
- **System Inventory**: Count and classify all building equipment
- **Load Estimation**: Based on equipment type and space served
- **Diversity Factors**: Applied based on building type and usage

## API Response Structure

### Complete Response Format
```json
{
  "building_data": {
    "spaces": [...],
    "building_elements": {...},
    "equipment": [...],
    "total_floor_area": 96.0,
    "building_info": {...},
    "hvac_systems": [...],
    "lighting_systems": [...],
    "electrical_systems": [...]
  },
  "electricity_consumption": {
    "lighting_consumption": 1440.0,
    "hvac_consumption": 5760.0, 
    "equipment_consumption": 2400.0,
    "total_annual_consumption": 9600.0,
    "energy_intensity": 100.0,
    "peak_demand": 4.8,
    "calculation_method": "Standard Building Energy Benchmarks"
  }
}
```

## Error Handling & Fallbacks

### 1. IFC Parsing Errors
- **Invalid File Format**: HTTP 400 with descriptive message
- **Corrupted IFC Data**: Graceful degradation with partial extraction
- **Missing Geometry**: Area estimation based on space count and type

### 2. Area Calculation Fallbacks
```python
if space_area == 0:
    if "PARK" in space_name:
        estimated_area = 25.0  # m² per parking space
    elif space_type == "OFFICE":
        estimated_area = 50.0  # m² per office space
    else:
        estimated_area = 20.0  # m² default
```

### 3. OpenAI Integration (Optional)
- **Primary**: AI-enhanced analysis for complex buildings
- **Fallback**: Standard benchmark calculations
- **Hybrid**: Combine AI insights with engineering calculations

## Performance Optimization

### 1. File Processing
- **Temporary Files**: Secure handling with automatic cleanup
- **Memory Management**: Efficient IFC object traversal
- **Concurrent Processing**: Support for multiple file uploads

### 2. Data Extraction Efficiency
- **Selective Parsing**: Extract only relevant IFC entities
- **Property Caching**: Cache frequently accessed property sets
- **Lazy Loading**: Load detailed properties only when needed

## Validation & Quality Assurance

### 1. Data Validation
- **Area Consistency**: Cross-check calculated vs. declared areas
- **Volume Validation**: Ensure realistic height assumptions
- **System Integration**: Verify equipment serves appropriate spaces

### 2. Energy Calculation Validation
- **Benchmark Comparison**: Compare against industry standards
- **Range Checking**: Flag unrealistic consumption values
- **Unit Consistency**: Ensure proper unit conversions

## Future Enhancements

### 1. Advanced Energy Modeling
- **Thermal Simulation**: Integration with EnergyPlus or similar
- **Weather Data**: Location-based climate adjustments
- **Operational Schedules**: Time-based energy profiles

### 2. Machine Learning Integration
- **Pattern Recognition**: Learn from building performance data
- **Predictive Analytics**: Forecast energy consumption trends
- **Optimization Recommendations**: Suggest efficiency improvements

### 3. Compliance Checking
- **Building Codes**: Automated code compliance verification
- **Energy Standards**: ASHRAE, LEED, BREEAM compliance
- **Accessibility**: ADA/accessibility requirement checking

## Technical Requirements

### Dependencies
```
fastapi==0.104.1          # Web framework
uvicorn==0.24.0           # ASGI server
ifcopenshell==0.8.3       # IFC processing
openai==0.28.1            # AI integration
python-dotenv==1.0.0      # Environment management
python-multipart==0.0.6   # File upload handling
```

### System Requirements
- **Python**: 3.8+
- **Memory**: 2GB+ for large IFC files
- **Storage**: Temporary space for file processing
- **Network**: Internet access for OpenAI API (optional)

## Deployment Considerations

### 1. Production Setup
- **HTTPS**: SSL/TLS encryption for file uploads
- **Authentication**: API key or OAuth integration
- **Rate Limiting**: Prevent abuse and ensure fair usage
- **Monitoring**: Log analysis and performance metrics

### 2. Scalability
- **Containerization**: Docker deployment
- **Load Balancing**: Multiple service instances
- **Caching**: Redis for frequently accessed calculations
- **Database**: Store building analysis results

This comprehensive system provides professional-grade building energy analysis capabilities through automated IFC file processing and advanced energy calculation algorithms.
