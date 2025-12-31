# ============================================================================
# Smart Agriculture Decision Support System - Streamlit Frontend
# Phase 5: Farmer-Facing Dashboard (FIXED - No ScriptRunContext Warnings)
# ============================================================================

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Optional
import os

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

# Set page config at the very top, before any other streamlit commands
st.set_page_config(
    page_title="Smart Agriculture Dashboard",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Get API URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
SENSOR_POLL_INTERVAL = 60  # seconds
CROP_OPTIONS = ["wheat", "corn", "soybeans", "tomato", "lettuce"]
GROWTH_STAGES = ["germination", "vegetative", "flowering", "fruiting", "maturation"]

# ============================================================================
# CSS STYLING
# ============================================================================

st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .alert-critical {
        background-color: #ffcccc;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #cc0000;
        margin: 10px 0;
    }
    .alert-warning {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 10px 0;
    }
    .recommendation-card {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION (Safe approach)
# ============================================================================

def init_session_state():
    """Initialize session state variables safely"""
    if "last_update" not in st.session_state:
        st.session_state.last_update = None
    
    if "current_crop" not in st.session_state:
        st.session_state.current_crop = "wheat"
    
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = "vegetative"
    
    if "sensor_data" not in st.session_state:
        st.session_state.sensor_data = None
    
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = None
    
    if "alerts" not in st.session_state:
        st.session_state.alerts = None

init_session_state()

# ============================================================================
# API HELPER FUNCTIONS (With better error handling)
# ============================================================================

# ============================================================================
# API CALL FUNCTIONS (No decorators at module level)
# ============================================================================

def fetch_sensor_status_raw(crop_id: Optional[str] = None):
    """Raw API call without caching"""
    url = f"{API_BASE_URL}/sensor/status"
    if crop_id:
        url += f"?crop_id={crop_id}"
    
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()

def fetch_recommendations_raw(crop_id: Optional[str] = None):
    """Raw API call without caching"""
    url = f"{API_BASE_URL}/recommendations"
    if crop_id:
        url += f"?crop_id={crop_id}"
    
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()

def fetch_alerts_raw(hours: int = 24):
    """Raw API call without caching"""
    url = f"{API_BASE_URL}/alerts?hours={hours}"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()

# ============================================================================
# USER-FACING API FUNCTIONS (With error handling)
# ============================================================================

def get_sensor_status(crop_id: Optional[str] = None):
    """Fetch current sensor readings from API"""
    try:
        return fetch_sensor_status_raw(crop_id)
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Is the backend running on http://localhost:8000?")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ API request timed out. Backend may be slow.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API Error: {str(e)}")
        return None

def get_recommendations(crop_id: Optional[str] = None):
    """Fetch AI-generated recommendations from API"""
    try:
        return fetch_recommendations_raw(crop_id)
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API.")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ API request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error fetching recommendations: {str(e)}")
        return None

def get_recent_alerts(hours: int = 24):
    """Fetch recent system alerts"""
    try:
        return fetch_alerts_raw(hours)
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API.")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ API request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error fetching alerts: {str(e)}")
        return None

def submit_sensor_reading(sensor_type: str, value: float, unit: str, crop_id: Optional[str] = None):
    """Submit a manual sensor reading"""
    try:
        url = f"{API_BASE_URL}/sensor/reading"
        payload = {
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "crop_id": crop_id,
            "timestamp": datetime.now().isoformat()
        }
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Is the backend running?")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to submit sensor reading: {str(e)}")
        return None

# ============================================================================
# UI COMPONENTS (Safe for Streamlit)
# ============================================================================

def display_sensor_card(sensor_name: str, sensor_data: dict):
    """Display a single sensor reading card"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if sensor_data:
            st.metric(
                label=f"📊 {sensor_name}",
                value=f"{sensor_data['value']:.1f}",
                delta=sensor_data.get('unit', '--')
            )
        else:
            st.metric(
                label=f"📊 {sensor_name}",
                value="N/A",
                delta="No data"
            )
    
    with col2:
        if sensor_data:
            try:
                ts = datetime.fromisoformat(sensor_data.get('timestamp', ''))
                age = datetime.now() - ts
                age_str = f"{int(age.total_seconds() / 60)} min ago"
                st.caption(f"📅 Last update: {age_str}")
            except:
                st.caption("📅 Timestamp unavailable")
        else:
            st.caption("📅 No data available")
    
    with col3:
        if sensor_data:
            st.success("✓ Active")
        else:
            st.warning("⚠ No recent data")

def display_recommendation_card(recommendation: dict):
    """Display a single recommendation in a formatted card"""
    priority_colors = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢"
    }
    
    priority = recommendation.get("priority", "low")
    icon = priority_colors.get(priority, "•")
    action = recommendation.get('action', 'Recommendation')
    confidence = recommendation.get('confidence', 0)
    rec_type = recommendation.get('recommendation_type', 'N/A').replace('_', ' ').title()
    
    st.markdown(f"""
    <div class='recommendation-card'>
        <h4>{icon} {action}</h4>
        <p><strong>Priority:</strong> {priority.upper()}</p>
        <p><strong>Confidence:</strong> {confidence:.0%}</p>
        <p><strong>Type:</strong> {rec_type}</p>
    </div>
    """, unsafe_allow_html=True)

def display_alert_card(alert: dict):
    """Display a system alert"""
    severity = alert.get("severity", "low")
    
    if severity == "critical":
        css_class = "alert-critical"
        icon = "🚨"
    elif severity in ["high", "warning"]:
        css_class = "alert-warning"
        icon = "⚠️"
    else:
        css_class = "alert-warning"
        icon = "ℹ️"
    
    alert_type = alert.get('alert_type', 'Alert').replace('_', ' ').upper()
    message = alert.get('message', 'No message')
    timestamp = alert.get('timestamp', 'Unknown time')
    
    st.markdown(f"""
    <div class='{css_class}'>
        <h4>{icon} {alert_type}</h4>
        <p>{message}</p>
        <p style='font-size: 0.9em; color: #666;'>{timestamp}</p>
    </div>
    """, unsafe_allow_html=True)

def display_explainability(recommendation: dict):
    """Display detailed reasoning behind a recommendation"""
    with st.expander("🔍 Show Decision Reasoning"):
        applied_rules = recommendation.get("applied_rules", [])
        
        if not applied_rules:
            st.info("No rule information available")
            return
        
        # Show all evaluated rules
        for rule in applied_rules:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(rule.get("rule_name", "Unknown Rule"))
                st.caption(rule.get("rule_description", "No description"))
            
            with col2:
                if rule.get("applicable"):
                    st.success("✓ Matched")
                else:
                    st.info("○ Not matched")
            
            # Show reasoning steps
            steps = rule.get("steps", [])
            if steps:
                step_texts = []
                for step in steps:
                    icon = "✓" if step.get("meets_condition") else "✗"
                    desc = step.get('description', 'Condition')
                    input_val = step.get('input_value', '?')
                    threshold = step.get('threshold', '?')
                    step_texts.append(
                        f"{icon} {desc} ({input_val} vs threshold {threshold})"
                    )
                
                for text in step_texts:
                    st.caption(text)
            
            st.markdown("---")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    
    # Header
    st.title("🌾 Smart Agriculture Decision Support System")
    st.markdown("*AI-powered irrigation and fertilization recommendations for data-driven farming*")
    
    # Sidebar: Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        crop_type = st.selectbox(
            "Select Crop",
            CROP_OPTIONS,
            index=CROP_OPTIONS.index(st.session_state.current_crop)
        )
        st.session_state.current_crop = crop_type
        
        growth_stage = st.selectbox(
            "Growth Stage",
            GROWTH_STAGES,
            index=GROWTH_STAGES.index(st.session_state.current_stage)
        )
        st.session_state.current_stage = growth_stage
        
        st.divider()
        
        # Manual sensor input
        st.subheader("📈 Add Manual Reading")
        with st.form("sensor_form", clear_on_submit=True):
            sensor_type = st.selectbox(
                "Sensor Type",
                ["soil_moisture", "temperature", "humidity"]
            )
            sensor_value = st.number_input("Value", min_value=-50.0, max_value=150.0, step=0.1, value=50.0)
            sensor_unit = st.text_input("Unit", value="%" if sensor_type == "soil_moisture" else "°C")
            
            submitted = st.form_submit_button("Submit Reading")
            
            if submitted:
                result = submit_sensor_reading(sensor_type, sensor_value, sensor_unit, crop_type)
                if result:
                    st.success(f"✓ Reading submitted (ID: {result.get('id', 'N/A')})")
                    st.session_state.last_update = datetime.now()
                    st.rerun()
        
        st.divider()
        st.caption(f"API: {API_BASE_URL}")
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "💡 Recommendations",
        "🚨 Alerts",
        "ℹ️ Help"
    ])
    
    # =====================================================================
    # TAB 1: DASHBOARD
    # =====================================================================
    with tab1:
        st.subheader("Current Sensor Readings")
        
        # Fetch and display sensor data
        sensor_status = get_sensor_status(crop_type)
        
        if sensor_status:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                display_sensor_card(
                    "Soil Moisture",
                    sensor_status.get("soil_moisture")
                )
            
            with col2:
                display_sensor_card(
                    "Temperature",
                    sensor_status.get("temperature")
                )
            
            with col3:
                display_sensor_card(
                    "Humidity",
                    sensor_status.get("humidity")
                )
        else:
            st.warning("⚠️ Unable to fetch sensor data. Check API connection.")
        
        # Display current conditions summary
        st.divider()
        st.subheader("📋 Current Conditions Summary")
        
        if sensor_status:
            conditions = []
            for sensor_type_key, data in sensor_status.items():
                if data:
                    conditions.append(
                        f"**{sensor_type_key.replace('_', ' ').title()}**: {data['value']:.1f} {data.get('unit', '?')}"
                    )
            
            if conditions:
                for cond in conditions:
                    st.markdown(cond)
            else:
                st.info("No sensor data available yet")
        else:
            st.info("No sensor data available")
        
        # Last update timestamp
        if st.session_state.last_update:
            st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True, key="refresh_dashboard"):
            st.rerun()
    
    # =====================================================================
    # TAB 2: RECOMMENDATIONS
    # =====================================================================
    with tab2:
        st.subheader("🤖 AI-Generated Recommendations")
        
        recommendations = get_recommendations(crop_type)
        
        if recommendations and "recommendations" in recommendations:
            recs = recommendations["recommendations"]
            
            if recs:
                for i, rec in enumerate(recs):
                    st.markdown(f"### Recommendation {i + 1}")
                    display_recommendation_card(rec)
                    
                    # Show explainability
                    try:
                        display_explainability(rec)
                    except Exception as e:
                        st.warning(f"Could not display reasoning: {str(e)}")
                    
                    st.divider()
            else:
                st.info("No recommendations at this time")
        else:
            st.info("Unable to generate recommendations. Check API or sensor data.")
        
        # Explanation of confidence score
        with st.expander("ℹ️ What does confidence mean?"):
            st.markdown("""
            The **confidence score** indicates how sure the system is about this recommendation:
            
            - **90-100%**: High confidence; follow recommendation
            - **70-90%**: Moderate confidence; use with judgment
            - **<70%**: Low confidence; verify with domain knowledge or additional data
            
            Confidence is affected by:
            - Data freshness (older data = lower confidence)
            - Number of matching rules
            - Historical accuracy of similar recommendations
            """)
        
        if st.button("🔄 Refresh Recommendations", use_container_width=True, key="refresh_recs"):
            st.rerun()
    
    # =====================================================================
    # TAB 3: ALERTS
    # =====================================================================
    with tab3:
        st.subheader("🚨 System Alerts")
        
        # Time range selector
        hours = st.slider("Show alerts from last", 1, 168, 24, help="Select time range in hours")
        
        alerts_data = get_recent_alerts(hours)
        
        if alerts_data and "alerts" in alerts_data:
            alerts = alerts_data["alerts"]
            
            if alerts:
                # Alert statistics
                col1, col2, col3 = st.columns(3)
                
                critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
                warning_count = sum(1 for a in alerts if a.get("severity") in ["high", "warning"])
                info_count = sum(1 for a in alerts if a.get("severity") in ["low", "info"])
                
                with col1:
                    st.metric("🔴 Critical", critical_count)
                with col2:
                    st.metric("🟠 Warning", warning_count)
                with col3:
                    st.metric("🟡 Info", info_count)
                
                st.divider()
                
                # Display each alert
                for alert in sorted(alerts, key=lambda x: x.get("severity", "low"), reverse=True):
                    display_alert_card(alert)
            else:
                st.success("✓ No alerts in selected time period")
        else:
            st.info("No alerts available")
        
        if st.button("🔄 Refresh Alerts", use_container_width=True, key="refresh_alerts"):
            st.rerun()
    
    # =====================================================================
    # TAB 4: HELP & DOCUMENTATION
    # =====================================================================
    with tab4:
        st.subheader("📖 User Guide")
        
        st.markdown("""
        ### How to Use This Dashboard
        
        **1. Configuration (Sidebar)**
        - Select your crop type
        - Specify current growth stage
        - Optionally add manual sensor readings
        
        **2. Dashboard Tab**
        - View real-time sensor readings (soil moisture, temperature, humidity)
        - Monitor current field conditions
        
        **3. Recommendations Tab**
        - Read AI-generated recommendations for irrigation and fertilization
        - Click "Show Decision Reasoning" to see why the recommendation was made
        - Confidence scores indicate recommendation reliability
        
        **4. Alerts Tab**
        - Review critical alerts (e.g., drought conditions)
        - Filter by time range
        - Take recommended remediation actions
        
        ### Understanding Recommendations
        
        Each recommendation includes:
        - **Action**: Specific task (e.g., "Increase irrigation to daily")
        - **Priority**: Critical, High, Medium, or Low
        - **Confidence**: 0-100% certainty
        - **Reasoning**: Which decision rules triggered this recommendation
        
        ### Tips for Best Results
        
        - **Provide accurate data**: Manual sensor readings help refine recommendations
        - **Update growth stage**: Recommendations vary by plant growth phase
        - **Monitor alerts closely**: Critical alerts require immediate action
        - **Review reasoning**: Understand *why* recommendations are made
        
        ### System Limitations
        
        ⚠️ This system provides *decision support*, not guarantees:
        - Recommendations should be validated with agronomic expertise
        - Sensor accuracy affects recommendation quality
        - Weather forecasts not yet integrated
        - Pest/disease detection not yet included
        
        ---
        
        **Version**: 0.1.0 (Prototype)  
        **Last Updated**: 2024
        """)
        
        st.divider()
        st.subheader("🔧 System Status")
        
        # Health check
        try:
            api_url = f"{API_BASE_URL.rsplit('/', 1)[0]}/health"
            response = requests.get(api_url, timeout=2)
            if response.status_code == 200:
                st.success("✓ API Server: Online")
            else:
                st.error("✗ API Server: Offline")
        except Exception as e:
            st.error(f"✗ API Server: Unreachable ({str(e)})")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()