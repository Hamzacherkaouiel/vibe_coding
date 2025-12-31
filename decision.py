# ============================================================================
# Smart Agriculture Decision Logic - Phase 4
# Improved Decision Engine with Explainability
# ============================================================================

from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import json

# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class CropType(str, Enum):
    """Supported crop types"""
    WHEAT = "wheat"
    CORN = "corn"
    SOYBEANS = "soybeans"
    TOMATO = "tomato"
    LETTUCE = "lettuce"

class GrowthStage(str, Enum):
    """Plant growth stages (simplified)"""
    GERMINATION = "germination"      # 0-2 weeks
    VEGETATIVE = "vegetative"        # 2-8 weeks
    FLOWERING = "flowering"          # 8-12 weeks
    FRUITING = "fruiting"            # 12-16 weeks
    MATURATION = "maturation"        # 16+ weeks

class RuleSeverity(str, Enum):
    """Confidence/severity of rule application"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ============================================================================
# DATA CLASSES FOR EXPLAINABILITY
# ============================================================================

@dataclass
class ExplanationStep:
    """Single step in decision reasoning"""
    description: str
    input_value: float
    threshold: float
    comparison: str  # "less_than", "greater_than", "in_range"
    meets_condition: bool

    def to_dict(self):
        return asdict(self)

@dataclass
class RuleApplication:
    """Records how a single rule was applied"""
    rule_id: str
    rule_name: str
    rule_description: str
    applicable: bool  # Did this rule's conditions match?
    severity: RuleSeverity
    steps: List[ExplanationStep]
    reasoning: str

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_description": self.rule_description,
            "applicable": self.applicable,
            "severity": self.severity.value,
            "steps": [s.to_dict() for s in self.steps],
            "reasoning": self.reasoning
        }

@dataclass
class RecommendationExplained:
    """Recommendation with full audit trail"""
    recommendation_type: str  # "irrigation", "fertilization", "pest_management"
    action: str
    confidence: float
    priority: str  # "low", "medium", "high"
    applied_rules: List[RuleApplication]
    timestamp: datetime = None
    crop_type: Optional[str] = None
    growth_stage: Optional[str] = None

    def to_dict(self):
        return {
            "recommendation_type": self.recommendation_type,
            "action": self.action,
            "confidence": self.confidence,
            "priority": self.priority,
            "applied_rules": [r.to_dict() for r in self.applied_rules],
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "crop_type": self.crop_type,
            "growth_stage": self.growth_stage,
            "summary": self.generate_summary()
        }

    def generate_summary(self) -> str:
        """Generate human-readable summary"""
        applicable_count = sum(1 for r in self.applied_rules if r.applicable)
        total_count = len(self.applied_rules)
        return f"{self.action} ({applicable_count}/{total_count} rules met condition; confidence: {self.confidence:.1%})"

@dataclass
class AlertExplained:
    """Alert with explanation of why it was triggered"""
    alert_type: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    triggered_by_rules: List[RuleApplication]
    remediation: str
    timestamp: datetime = None

    def to_dict(self):
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "triggered_by_rules": [r.to_dict() for r in self.triggered_by_rules],
            "remediation": self.remediation,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

# ============================================================================
# RULE CONFIGURATION (EXTERNALIZED)
# ============================================================================

IRRIGATION_RULES = {
    "rule_001": {
        "name": "Low Soil Moisture - Warm Weather",
        "description": "Trigger irrigation when soil moisture is low and temperature is elevated (high evapotranspiration)",
        "enabled": True,
        "crop_types": ["wheat", "corn", "soybeans"],
        "conditions": {
            "soil_moisture": {"operator": "<", "value": 25.0, "unit": "%"},
            "temperature": {" operator": ">", "value": 28.0, "unit": "°C"}
        },
        "action": "Increase irrigation frequency to daily",
        "priority": "high",
        "confidence_base": 0.95
    },
    "rule_002": {
        "name": "Low Soil Moisture - Normal Weather",
        "description": "Moderate irrigation when soil moisture is low but temperature is moderate",
        "enabled": True,
        "crop_types": ["wheat", "corn", "soybeans", "tomato", "lettuce"],
        "conditions": {
            "soil_moisture": {"operator": "<", "value": 25.0, "unit": "%"},
            "temperature": {"operator": "<=", "value": 28.0, "unit": "°C"}
        },
        "action": "Increase irrigation to every 2 days",
        "priority": "medium",
        "confidence_base": 0.85
    },
    "rule_003": {
        "name": "Critical Drought Risk",
        "description": "Severe drought condition requiring immediate intervention",
        "enabled": True,
        "crop_types": ["wheat", "corn", "soybeans", "tomato", "lettuce"],
        "conditions": {
            "soil_moisture": {"operator": "<", "value": 10.0, "unit": "%"}
        },
        "action": "CRITICAL: Immediate daily irrigation required + irrigation system check",
        "priority": "critical",
        "confidence_base": 0.98
    },
    "rule_004": {
        "name": "Overwatering Risk",
        "description": "Soil moisture is too high; risk of root rot and nutrient leaching",
        "enabled": True,
        "crop_types": ["tomato", "lettuce"],
        "conditions": {
            "soil_moisture": {"operator": ">", "value": 85.0, "unit": "%"},
            "humidity": {"operator": ">", "value": 80.0, "unit": "%"}
        },
        "action": "Reduce irrigation; ensure proper drainage; monitor for fungal disease",
        "priority": "medium",
        "confidence_base": 0.80
    },
    "rule_005": {
        "name": "Optimal Soil Moisture",
        "description": "Soil moisture is within ideal range for current crop",
        "enabled": True,
        "crop_types": ["wheat", "corn", "soybeans", "tomato", "lettuce"],
        "conditions": {
            "soil_moisture": {"operator": ">=", "value": 40.0, "unit": "%"},
            "soil_moisture": {"operator": "<=", "value": 70.0, "unit": "%"}
        },
        "action": "Maintain current irrigation schedule",
        "priority": "low",
        "confidence_base": 0.90
    }
}

FERTILIZATION_RULES = {
    "rule_101": {
        "name": "Early Season Nitrogen Boost - Vegetative Stage",
        "description": "Apply nitrogen-rich fertilizer during vegetative growth stage",
        "enabled": True,
        "crop_types": ["corn", "wheat"],
        "conditions": {
            "growth_stage": {"operator": "==", "value": "vegetative"},
            "soil_nitrogen": {"operator": "<", "value": 30.0, "unit": "mg/kg"}
        },
        "action": "Apply nitrogen fertilizer (N:P:K = 3:1:1) at recommended rate",
        "priority": "high",
        "confidence_base": 0.90
    },
    "rule_102": {
        "name": "Phosphorus for Root Development",
        "description": "Phosphorus supports root system development in germination stage",
        "enabled": True,
        "crop_types": ["wheat", "corn", "soybeans"],
        "conditions": {
            "growth_stage": {"operator": "==", "value": "germination"},
            "soil_phosphorus": {"operator": "<", "value": 20.0, "unit": "mg/kg"}
        },
        "action": "Apply phosphorus-rich starter fertilizer",
        "priority": "high",
        "confidence_base": 0.88
    }
}

# ============================================================================
# IMPROVED DECISION ENGINE WITH EXPLAINABILITY
# ============================================================================

class ImprovedDecisionEngine:
    """Decision engine with full explainability and rule-based logic"""

    def __init__(self, config: Dict = None):
        """Initialize with optional configuration"""
        self.irrigation_rules = IRRIGATION_RULES
        self.fertilization_rules = FERTILIZATION_RULES
        self.config = config or {}

    def compare_value(self, actual: float, operator: str, threshold: float) -> bool:
        """Evaluate if actual value meets threshold given operator"""
        if operator == "<":
            return actual < threshold
        elif operator == ">":
            return actual > threshold
        elif operator == "<=":
            return actual <= threshold
        elif operator == ">=":
            return actual >= threshold
        elif operator == "==":
            return actual == threshold
        elif operator == "!=":
            return actual != threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")

    def generate_irrigation_recommendation(
        self,
        soil_moisture: float,
        temperature: float,
        humidity: Optional[float] = None,
        crop_type: str = "wheat",
        growth_stage: str = "vegetative"
    ) -> RecommendationExplained:
        """
        Generate irrigation recommendation with full explainability.

        Args:
            soil_moisture: Current soil moisture (%)
            temperature: Current temperature (°C)
            humidity: Current relative humidity (%)
            crop_type: Type of crop being grown
            growth_stage: Current growth stage

        Returns:
            RecommendationExplained object with full audit trail
        """

        applied_rules = []
        highest_priority = "low"
        highest_confidence = 0.0
        recommended_action = "Maintain current irrigation schedule"

        # Evaluate each enabled rule
        for rule_id, rule_config in self.irrigation_rules.items():
            if not rule_config["enabled"]:
                continue

            # Check if rule applies to this crop
            if crop_type not in rule_config["crop_types"]:
                continue

            # Evaluate all conditions
            steps = []
            all_conditions_met = True

            for condition_name, condition_spec in rule_config["conditions"].items():
                operator = condition_spec.get("operator")
                threshold = condition_spec.get("value")

                # Map condition name to actual sensor value
                if condition_name == "soil_moisture":
                    actual_value = soil_moisture
                elif condition_name == "temperature":
                    actual_value = temperature
                elif condition_name == "humidity":
                    actual_value = humidity or 0.0
                else:
                    actual_value = None

                if actual_value is not None:
                    condition_met = self.compare_value(actual_value, operator, threshold)
                    steps.append(
                        ExplanationStep(
                            description=f"{condition_name} {operator} {threshold}",
                            input_value=actual_value,
                            threshold=threshold,
                            comparison=operator,
                            meets_condition=condition_met
                        )
                    )

                    if not condition_met:
                        all_conditions_met = False

            # If all conditions are met, record this rule application
            if all_conditions_met:
                rule_app = RuleApplication(
                    rule_id=rule_id,
                    rule_name=rule_config["name"],
                    rule_description=rule_config["description"],
                    applicable=True,
                    severity=RuleSeverity(rule_config["priority"]),
                    steps=steps,
                    reasoning=f"All conditions satisfied for '{rule_config['name']}'"
                )
                applied_rules.append(rule_app)

                # Update recommended action if this rule has higher priority
                if self._priority_to_int(rule_config["priority"]) > self._priority_to_int(highest_priority):
                    highest_priority = rule_config["priority"]
                    recommended_action = rule_config["action"]
                    highest_confidence = rule_config["confidence_base"]
            else:
                # Still record rule, but mark as not applicable
                rule_app = RuleApplication(
                    rule_id=rule_id,
                    rule_name=rule_config["name"],
                    rule_description=rule_config["description"],
                    applicable=False,
                    severity=RuleSeverity(rule_config["priority"]),
                    steps=steps,
                    reasoning=f"Not all conditions met. {', '.join([s.description for s in steps if not s.meets_condition])} not satisfied."
                )
                applied_rules.append(rule_app)

        # Adjust confidence based on data freshness (mock)
        final_confidence = highest_confidence * 0.95  # 5% discount for data age

        recommendation = RecommendationExplained(
            recommendation_type="irrigation",
            action=recommended_action,
            confidence=final_confidence,
            priority=highest_priority,
            applied_rules=applied_rules,
            timestamp=datetime.now(),
            crop_type=crop_type,
            growth_stage=growth_stage
        )

        return recommendation

    def check_drought_alert(
        self,
        soil_moisture: float,
        crop_type: str = "wheat"
    ) -> Optional[AlertExplained]:
        """
        Generate drought alert if conditions warrant, with explanation.
        """

        triggered_rules = []

        # Critical drought
        if soil_moisture < 10.0:
            rule_app = RuleApplication(
                rule_id="alert_001",
                rule_name="Critical Drought",
                rule_description="Soil moisture critically low",
                applicable=True,
                severity=RuleSeverity.CRITICAL,
                steps=[
                    ExplanationStep(
                        description="soil_moisture < 10.0%",
                        input_value=soil_moisture,
                        threshold=10.0,
                        comparison="<",
                        meets_condition=True
                    )
                ],
                reasoning="Critical threshold breached."
            )
            triggered_rules.append(rule_app)

            return AlertExplained(
                alert_type="drought_critical",
                severity="critical",
                message=f"CRITICAL: Soil moisture at {soil_moisture:.1f}%. Immediate intervention required!",
                triggered_by_rules=triggered_rules,
                remediation="Immediately activate emergency irrigation. Check irrigation system for failures. Monitor every 2-4 hours.",
                timestamp=datetime.now()
            )

        # Moderate drought warning
        elif soil_moisture < 25.0:
            rule_app = RuleApplication(
                rule_id="alert_002",
                rule_name="Drought Warning",
                rule_description="Soil moisture below optimal threshold",
                applicable=True,
                severity=RuleSeverity.HIGH,
                steps=[
                    ExplanationStep(
                        description="soil_moisture < 25.0%",
                        input_value=soil_moisture,
                        threshold=25.0,
                        comparison="<",
                        meets_condition=True
                    )
                ],
                reasoning="Threshold for drought warning breached."
            )
            triggered_rules.append(rule_app)

            return AlertExplained(
                alert_type="drought_warning",
                severity="high",
                message=f"WARNING: Soil moisture at {soil_moisture:.1f}%. Plant stress risk increasing.",
                triggered_by_rules=triggered_rules,
                remediation="Increase irrigation frequency over next 24-48 hours. Monitor soil moisture closely.",
                timestamp=datetime.now()
            )

        return None

    @staticmethod
    def _priority_to_int(priority: str) -> int:
        """Convert priority string to numeric value for comparison"""
        priority_map = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_map.get(priority, 0)


# ============================================================================
# EXAMPLE USAGE & TESTING
# ============================================================================

if __name__ == "__main__":
    engine = ImprovedDecisionEngine()

    # Scenario 1: Low soil moisture + high temperature
    print("=" * 70)
    print("SCENARIO 1: Low soil moisture, high temperature")
    print("=" * 70)
    rec1 = engine.generate_irrigation_recommendation(
        soil_moisture=20.0,
        temperature=32.0,
        humidity=45.0,
        crop_type="corn",
        growth_stage="vegetative"
    )
    print(json.dumps(rec1.to_dict(), indent=2))

    # Scenario 2: Critical drought
    print("\n" + "=" * 70)
    print("SCENARIO 2: Critical drought alert")
    print("=" * 70)
    alert = engine.check_drought_alert(soil_moisture=8.0, crop_type="wheat")
    if alert:
        print(json.dumps(alert.to_dict(), indent=2))

    # Scenario 3: Optimal conditions
    print("\n" + "=" * 70)
    print("SCENARIO 3: Optimal soil moisture conditions")
    print("=" * 70)
    rec3 = engine.generate_irrigation_recommendation(
        soil_moisture=55.0,
        temperature=22.0,
        humidity=65.0,
        crop_type="tomato",
        growth_stage="fruiting"
    )
    print(json.dumps(rec3.to_dict(), indent=2))