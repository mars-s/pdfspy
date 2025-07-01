"""
Hazard classification system for chemical entities.
Classifies H-codes into categories and determines signal words.
"""
from typing import Dict, List


class HazardClassifier:
    def __init__(self):
        self.hazard_classes = self._build_hazard_classification()

    def classify_hazard_statements(self, h_codes: List[str]) -> Dict[str, List[str]]:
        """Classify H-codes into hazard categories"""
        classification = {
            'physical_hazards': [],
            'health_hazards': [],
            'environmental_hazards': []
        }

        for code in h_codes:
            if not code.startswith('H'):
                continue
                
            try:
                code_num = int(code[1:4])  # Extract numeric part (H123 -> 123)
                
                if 200 <= code_num <= 299:
                    classification['physical_hazards'].append(code)
                elif 300 <= code_num <= 399:
                    classification['health_hazards'].append(code)
                elif 400 <= code_num <= 499:
                    classification['environmental_hazards'].append(code)
            except ValueError:
                # Handle codes with letters after numbers (e.g., H315a)
                continue

        return classification

    def determine_signal_word(self, h_codes: List[str]) -> str:
        """Determine signal word based on H-codes"""
        danger_codes = [
            'H200', 'H201', 'H202', 'H203', 'H204', 'H205',  # Explosives
            'H220', 'H222', 'H224',  # Highly flammable
            'H240', 'H241', 'H250', 'H260', 'H271',  # Reactive
            'H280',  # Compressed gas
            'H300', 'H301', 'H310', 'H311', 'H330', 'H331',  # Acute toxicity
            'H314', 'H318',  # Corrosive
            'H334',  # Respiratory sensitizer
            'H340', 'H350', 'H360', 'H370', 'H372',  # Chronic effects
            'H400', 'H410'  # Environmental
        ]

        warning_codes = [
            'H205', 'H221', 'H223', 'H225', 'H226', 'H227', 'H228',  # Flammable
            'H241', 'H242', 'H251', 'H252', 'H261', 'H270', 'H272',  # Reactive
            'H281', 'H290',  # Other physical
            'H302', 'H303', 'H304', 'H305', 'H312', 'H313', 'H315', 'H316',  # Health
            'H317', 'H319', 'H320', 'H332', 'H333', 'H335', 'H336',  # Health continued
            'H341', 'H351', 'H361', 'H362', 'H371', 'H373',  # Chronic
            'H401', 'H402', 'H411', 'H412', 'H413', 'H420'  # Environmental
        ]

        # Check for DANGER codes first (highest priority)
        for code in h_codes:
            if code in danger_codes:
                return 'DANGER'

        # Check for WARNING codes
        for code in h_codes:
            if code in warning_codes:
                return 'WARNING'

        return 'None' if not h_codes else 'WARNING'  # Default to WARNING if codes exist

    def get_hazard_category_summary(self, h_codes: List[str]) -> Dict[str, any]:
        """Get comprehensive hazard category analysis"""
        classification = self.classify_hazard_statements(h_codes)
        signal_word = self.determine_signal_word(h_codes)
        
        # Determine primary hazard type
        primary_hazard = self._determine_primary_hazard(classification)
        
        # Get severity level
        severity = self._calculate_severity_score(h_codes)
        
        return {
            'signal_word': signal_word,
            'primary_hazard_type': primary_hazard,
            'severity_score': severity,
            'classification': classification,
            'total_hazards': len(h_codes),
            'requires_special_handling': severity >= 8 or signal_word == 'DANGER'
        }

    def _determine_primary_hazard(self, classification: Dict[str, List[str]]) -> str:
        """Determine the primary hazard type based on classification"""
        if classification['health_hazards']:
            return 'health'
        elif classification['physical_hazards']:
            return 'physical'
        elif classification['environmental_hazards']:
            return 'environmental'
        else:
            return 'none'

    def _calculate_severity_score(self, h_codes: List[str]) -> int:
        """Calculate severity score (1-10) based on H-codes"""
        high_severity_codes = [
            'H200', 'H201', 'H300', 'H310', 'H330', 'H314', 'H318',
            'H340', 'H350', 'H360', 'H370', 'H400', 'H410'
        ]
        
        medium_severity_codes = [
            'H220', 'H224', 'H240', 'H301', 'H311', 'H331', 'H315',
            'H319', 'H334', 'H341', 'H351', 'H361', 'H371', 'H401'
        ]
        
        score = 0
        for code in h_codes:
            if code in high_severity_codes:
                score += 3
            elif code in medium_severity_codes:
                score += 2
            else:
                score += 1
        
        return min(score, 10)  # Cap at 10

    def _build_hazard_classification(self):
        """Build comprehensive hazard classification system"""
        return {
            'explosive': {
                'codes': ['H200', 'H201', 'H202', 'H203', 'H204', 'H205'],
                'description': 'Explosive substances and mixtures'
            },
            'flammable_gas': {
                'codes': ['H220', 'H221'],
                'description': 'Flammable gases'
            },
            'flammable_aerosol': {
                'codes': ['H222', 'H223'],
                'description': 'Flammable aerosols'
            },
            'flammable_liquid': {
                'codes': ['H224', 'H225', 'H226', 'H227'],
                'description': 'Flammable liquids'
            },
            'flammable_solid': {
                'codes': ['H228'],
                'description': 'Flammable solids'
            },
            'self_reactive': {
                'codes': ['H240', 'H241', 'H242'],
                'description': 'Self-reactive substances'
            },
            'pyrophoric': {
                'codes': ['H250', 'H251', 'H252'],
                'description': 'Pyrophoric substances'
            },
            'water_reactive': {
                'codes': ['H260', 'H261'],
                'description': 'Water-reactive substances'
            },
            'oxidizing': {
                'codes': ['H270', 'H271', 'H272'],
                'description': 'Oxidizing substances'
            },
            'compressed_gas': {
                'codes': ['H280', 'H281'],
                'description': 'Gases under pressure'
            },
            'corrosive_metal': {
                'codes': ['H290'],
                'description': 'Corrosive to metals'
            },
            'acute_toxicity_oral': {
                'codes': ['H300', 'H301', 'H302', 'H303'],
                'description': 'Acute toxicity - oral'
            },
            'acute_toxicity_dermal': {
                'codes': ['H310', 'H311', 'H312', 'H313'],
                'description': 'Acute toxicity - dermal'
            },
            'acute_toxicity_inhalation': {
                'codes': ['H330', 'H331', 'H332', 'H333'],
                'description': 'Acute toxicity - inhalation'
            },
            'aspiration_hazard': {
                'codes': ['H304', 'H305'],
                'description': 'Aspiration hazard'
            },
            'skin_corrosion': {
                'codes': ['H314'],
                'description': 'Skin corrosion/irritation'
            },
            'skin_irritation': {
                'codes': ['H315', 'H316'],
                'description': 'Skin irritation'
            },
            'skin_sensitization': {
                'codes': ['H317'],
                'description': 'Skin sensitization'
            },
            'eye_damage': {
                'codes': ['H318', 'H319', 'H320'],
                'description': 'Serious eye damage/irritation'
            },
            'respiratory_sensitization': {
                'codes': ['H334'],
                'description': 'Respiratory sensitization'
            },
            'respiratory_irritation': {
                'codes': ['H335'],
                'description': 'Respiratory tract irritation'
            },
            'narcotic_effects': {
                'codes': ['H336'],
                'description': 'Narcotic effects'
            },
            'germ_cell_mutagenicity': {
                'codes': ['H340', 'H341'],
                'description': 'Germ cell mutagenicity'
            },
            'carcinogenicity': {
                'codes': ['H350', 'H351'],
                'description': 'Carcinogenicity'
            },
            'reproductive_toxicity': {
                'codes': ['H360', 'H361', 'H362'],
                'description': 'Reproductive toxicity'
            },
            'target_organ_toxicity_single': {
                'codes': ['H370', 'H371'],
                'description': 'Specific target organ toxicity - single exposure'
            },
            'target_organ_toxicity_repeated': {
                'codes': ['H372', 'H373'],
                'description': 'Specific target organ toxicity - repeated exposure'
            },
            'aquatic_toxicity_acute': {
                'codes': ['H400', 'H401', 'H402'],
                'description': 'Hazardous to aquatic environment - acute'
            },
            'aquatic_toxicity_chronic': {
                'codes': ['H410', 'H411', 'H412', 'H413'],
                'description': 'Hazardous to aquatic environment - chronic'
            },
            'ozone_layer': {
                'codes': ['H420'],
                'description': 'Hazardous to the ozone layer'
            }
        }
