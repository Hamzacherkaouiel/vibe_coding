# ============================================================================
# Smart Agriculture Decision Support System - FastAPI Backend
# Phase 3: AI-Generated Prototype Code (With Human Annotations)
# ============================================================================

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import sqlite3
import json
import os

# ============================================================================
# DATA MODELS (DTOs - Data Transfer Objects)
# ============================================================================

class SensorReading(BaseModel):
    """Represents a single sensor measurement"""
    sensor_type: str  # "soil_moisture", "temperature", "humidity"
    value: float
    unit: str         # "%", "°C", "RH%"
    timestamp: Optional[datetime] = None
    crop_id: Optional[str] = None

class Recommendation(BaseModel):
    """Represents a system recommendation"""
    recommendation_type: str  # "irrigation" or "fertilization"
    action: str
    confidence: float  # 0.0 to 1.0
    explanation: str
    timestamp: Optional[datetime] = None

class Alert(BaseModel):
    """Represents a system alert"""
    alert_type: str  # "drought", "overwatering", etc.
    severity: str    # "low", "medium", "high"
    message: str
    timestamp: Optional[datetime] = None

# ============================================================================
# INFRASTRUCTURE: DATABASE SETUP
# ============================================================================

DB_PATH = "agriculture.db"

def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # ANNOTATION (Human): Schema is reasonable but lacks indexes on frequently queried fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            crop_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_type TEXT NOT NULL,
            action TEXT NOT NULL,
            confidence REAL NOT NULL,
            explanation TEXT NOT NULL,
            crop_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            crop_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ANNOTATION (Human): Missing rules table - should be added for configuration management
    
    conn.commit()
    conn.close()

# ============================================================================
# DATA ACCESS LAYER (DAL)
# ============================================================================

class SensorRepository:
    """Handles all sensor data persistence"""
    
    @staticmethod
    def save_reading(reading: SensorReading) -> int:
        """Save a sensor reading to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # ANNOTATION (Human): No validation that sensor_type is valid
        cursor.execute('''
            INSERT INTO sensor_readings (sensor_type, value, unit, crop_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            reading.sensor_type,
            reading.value,
            reading.unit,
            reading.crop_id,
            reading.timestamp or datetime.now()
        ))
        
        conn.commit()
        reading_id = cursor.lastrowid
        conn.close()
        return reading_id
    
    @staticmethod
    def get_latest_reading(sensor_type: str, crop_id: Optional[str] = None) -> Optional[dict]:
        """Retrieve the most recent reading of a given sensor type"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if crop_id:
            # ANNOTATION (Human): Query could be parameterized better
            cursor.execute('''
                SELECT sensor_type, value, unit, timestamp FROM sensor_readings
                WHERE sensor_type = ? AND crop_id = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (sensor_type, crop_id))
        else:
            cursor.execute('''
                SELECT sensor_type, value, unit, timestamp FROM sensor_readings
                WHERE sensor_type = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (sensor_type,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "sensor_type": row[0],
                "value": row[1],
                "unit": row[2],
                "timestamp": row[3]
            }
        return None
    
    @staticmethod
    def get_readings_range(sensor_type: str, hours: int = 24) -> List[dict]:
        """Retrieve readings from last N hours"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sensor_type, value, unit, timestamp FROM sensor_readings
            WHERE sensor_type = ? AND timestamp > datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp ASC
        ''', (sensor_type, hours))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{"sensor_type": r[0], "value": r[1], "unit": r[2], "timestamp": r[3]} for r in rows]


class RecommendationRepository:
    """Handles recommendation persistence and retrieval"""
    
    @staticmethod
    def save_recommendation(recommendation: Recommendation) -> int:
        """Save a recommendation to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO recommendations (recommendation_type, action, confidence, explanation, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            recommendation.recommendation_type,
            recommendation.action,
            recommendation.confidence,
            recommendation.explanation,
            recommendation.timestamp or datetime.now()
        ))
        
        conn.commit()
        rec_id = cursor.lastrowid
        conn.close()
        return rec_id


class AlertRepository:
    """Handles alert persistence"""
    
    @staticmethod
    def save_alert(alert: Alert) -> int:
        """Save an alert"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (alert_type, severity, message, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (
            alert.alert_type,
            alert.severity,
            alert.message,
            alert.timestamp or datetime.now()
        ))
        
        conn.commit()
        alert_id = cursor.lastrowid
        conn.close()
        return alert_id
    
    @staticmethod
    def get_recent_alerts(hours: int = 24) -> List[dict]:
        """Get alerts from last N hours"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT alert_type, severity, message, timestamp FROM alerts
            WHERE timestamp > datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp DESC
        ''', (hours,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{"alert_type": r[0], "severity": r[1], "message": r[2], "timestamp": r[3]} for r in rows]


# ============================================================================
# BUSINESS LOGIC LAYER
# ============================================================================

class DecisionEngine:
    """Core decision logic for recommendations"""
    
    # ANNOTATION (Human): These thresholds should be externalized to a config file/database
    IRRIGATION_THRESHOLDS = {
        "soil_moisture_low": 25.0,      # % - trigger irrigation
        "soil_moisture_critical": 10.0  # % - drought alert
    }
    
    FERTILIZER_THRESHOLDS = {
        "nitrogen_low": 20.0  # mg/kg
    }
    
    @staticmethod
    def generate_irrigation_recommendation(soil_moisture: float, temperature: float) -> Recommendation:
        """
        Generate irrigation recommendation based on soil moisture and temperature.
        ANNOTATION (Human): Rule is simplistic. Real agronomic rules would be more complex.
        """
        
        if soil_moisture < DecisionEngine.IRRIGATION_THRESHOLDS["soil_moisture_low"]:
            if temperature > 30:
                action = "Increase irrigation frequency to daily"
                confidence = 0.95
                explanation = f"Soil moisture ({soil_moisture}%) is low and temperature is high ({temperature}°C). High evapotranspiration risk."
            else:
                action = "Increase irrigation to every 2 days"
                confidence = 0.85
                explanation = f"Soil moisture ({soil_moisture}%) is below optimal level ({DecisionEngine.IRRIGATION_THRESHOLDS['soil_moisture_low']}%)."
        else:
            action = "Current irrigation schedule is adequate"
            confidence = 0.90
            explanation = f"Soil moisture ({soil_moisture}%) is within acceptable range."
        
        return Recommendation(
            recommendation_type="irrigation",
            action=action,
            confidence=confidence,
            explanation=explanation,
            timestamp=datetime.now()
        )
    
    @staticmethod
    def check_drought_risk(soil_moisture: float) -> Optional[Alert]:
        """Generate drought alert if conditions warrant"""
        if soil_moisture < DecisionEngine.IRRIGATION_THRESHOLDS["soil_moisture_critical"]:
            return Alert(
                alert_type="drought",
                severity="high",
                message=f"CRITICAL: Soil moisture at {soil_moisture}%. Immediate irrigation required.",
                timestamp=datetime.now()
            )
        elif soil_moisture < DecisionEngine.IRRIGATION_THRESHOLDS["soil_moisture_low"]:
            return Alert(
                alert_type="drought_warning",
                severity="medium",
                message=f"WARNING: Soil moisture below optimal ({soil_moisture}%). Plan irrigation.",
                timestamp=datetime.now()
            )
        return None


# ============================================================================
# SERVICE LAYER
# ============================================================================

class SensorService:
    """Handles sensor data ingestion and validation"""
    
    @staticmethod
    def ingest_reading(reading: SensorReading) -> dict:
        """
        Ingest and validate sensor data.
        ANNOTATION (Human): Validation is minimal. Should check value ranges per sensor type.
        """
        
        # ANNOTATION (Human): SECURITY: No input sanitization
        if reading.value < -50 or reading.value > 150:
            raise HTTPException(status_code=400, detail="Sensor value out of realistic range")
        
        reading_id = SensorRepository.save_reading(reading)
        return {"id": reading_id, "status": "recorded"}
    
    @staticmethod
    def get_current_status(crop_id: Optional[str] = None) -> dict:
        """Get current sensor readings"""
        return {
            "soil_moisture": SensorRepository.get_latest_reading("soil_moisture", crop_id),
            "temperature": SensorRepository.get_latest_reading("temperature", crop_id),
            "humidity": SensorRepository.get_latest_reading("humidity", crop_id)
        }


class RecommendationService:
    """Generates recommendations based on current conditions"""
    
    @staticmethod
    def generate_recommendations(crop_id: Optional[str] = None) -> dict:
        """Generate all recommendations for current conditions"""
        
        # Get latest sensor readings
        status = SensorService.get_current_status(crop_id)
        
        # ANNOTATION (Human): Error handling is weak if sensors haven't reported yet
        if not status["soil_moisture"]:
            raise HTTPException(status_code=503, detail="No soil moisture data available")
        
        soil_moisture = status["soil_moisture"]["value"]
        temperature = status["temperature"]["value"] if status["temperature"] else 25.0
        
        # Generate irrigation recommendation
        irrig_rec = DecisionEngine.generate_irrigation_recommendation(soil_moisture, temperature)
        irrig_id = RecommendationRepository.save_recommendation(irrig_rec)
        
        # Check for alerts
        alerts = []
        drought_alert = DecisionEngine.check_drought_risk(soil_moisture)
        if drought_alert:
            alert_id = AlertRepository.save_alert(drought_alert)
            alerts.append(drought_alert.dict())
        
        return {
            "recommendations": [irrig_rec.dict()],
            "alerts": alerts,
            "current_conditions": status
        }


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(title="Smart Agriculture Decision Support System", version="0.1.0")

# Add CORS middleware
# ANNOTATION (Human): SECURITY: CORS is open to all origins. Restrict in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    if not os.path.exists(DB_PATH):
        init_db()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/api/sensor/reading")
async def post_sensor_reading(reading: SensorReading):
    """
    Ingest a sensor reading.
    ANNOTATION (Human): Should validate sensor_type against allowed values.
    """
    try:
        result = SensorService.ingest_reading(reading)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        # ANNOTATION (Human): SECURITY: Exposing exception details in response
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensor/status")
async def get_sensor_status(crop_id: Optional[str] = None):
    """Get current sensor readings"""
    return SensorService.get_current_status(crop_id)

@app.get("/api/recommendations")
async def get_recommendations(crop_id: Optional[str] = None):
    """
    Generate recommendations based on current sensor data.
    """
    try:
        result = RecommendationService.generate_recommendations(crop_id)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error generating recommendations")

@app.get("/api/alerts")
async def get_alerts(hours: int = 24):
    """Get recent alerts"""
    return {"alerts": AlertRepository.get_recent_alerts(hours)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "agriculture-api"}

# ============================================================================
# RUN THE APPLICATION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)