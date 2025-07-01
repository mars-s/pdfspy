"""
Chemical Named Entity Recognition system for PDF extraction.
Optimized for Safety Data Sheets and chemical documents.
"""
import re
from typing import Dict, List, Tuple
import json
from pathlib import Path


class ChemicalNER:
    def __init__(self):
        self.patterns = self._load_chemical_patterns()
        self.dictionaries = self._load_chemical_dictionaries()

    def _load_chemical_patterns(self):
        """Pre-compiled regex patterns for chemical entities"""
        return {
            'cas_number': re.compile(r'\b(\d{2,7}-\d{2}-\d)\b'),
            'ec_number': re.compile(r'\b(\d{3}-\d{3}-\d)\b'),
            'reach_registration': re.compile(r'\b(\d{2}-\d{10}-\d{2}-[a-zA-Z0-9])\b'),
            'hazard_statement': re.compile(r'\b(H\d{3}[A-Za-z]*)\b'),
            'precautionary_statement': re.compile(r'\b(P\d{3}[A-Za-z]*)\b'),
            'signal_word': re.compile(r'\b(DANGER|WARNING|CAUTION)\b', re.IGNORECASE),
            'pictogram': re.compile(r'GHS\d{2}', re.IGNORECASE),
            'concentration_range': re.compile(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%'),
            'concentration_exact': re.compile(r'(\d+(?:\.\d+)?)\s*%'),
            'boiling_point': re.compile(r'(\d+(?:\.\d+)?)\s*°?C', re.IGNORECASE),
            'molecular_weight': re.compile(r'(\d+(?:\.\d+)?)\s*g/mol', re.IGNORECASE),
            'flash_point': re.compile(r'flash\s*point[:\s]*(\d+(?:\.\d+)?)\s*°?C', re.IGNORECASE),
            'melting_point': re.compile(r'melting\s*point[:\s]*(\d+(?:\.\d+)?)\s*°?C', re.IGNORECASE),
            'density': re.compile(r'(\d+(?:\.\d+)?)\s*g/cm³?', re.IGNORECASE),
            'ph_value': re.compile(r'pH[:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE),
        }

    def _load_chemical_dictionaries(self):
        """Load chemical substance dictionaries"""
        return {
            'hazard_statements': self._load_hazard_statements(),
            'pictogram_meanings': self._load_pictogram_meanings(),
            'chemical_synonyms': self._load_chemical_synonyms()
        }

    def extract_entities(self, text: str) -> Dict[str, List[Tuple[str, int, int]]]:
        """Extract all chemical entities from text"""
        entities = {}

        for entity_type, pattern in self.patterns.items():
            matches = []
            for match in pattern.finditer(text):
                matches.append((
                    match.group(1) if match.groups() else match.group(0),
                    match.start(),
                    match.end()
                ))
            entities[entity_type] = matches

        return entities

    def validate_cas_number(self, cas: str) -> bool:
        """Validate CAS number using check digit"""
        if not re.match(r'^\d{2,7}-\d{2}-\d$', cas):
            return False

        # CAS check digit validation
        digits = cas.replace('-', '')
        check_digit = int(digits[-1])
        calculated = sum(int(d) * (i + 1) for i, d in enumerate(digits[-2::-1])) % 10

        return check_digit == calculated

    def extract_chemical_info(self, text: str) -> Dict[str, any]:
        """Extract comprehensive chemical information"""
        entities = self.extract_entities(text)
        
        # Validate CAS numbers
        valid_cas = []
        for cas, _, _ in entities.get('cas_number', []):
            if self.validate_cas_number(cas):
                valid_cas.append(cas)

        # Get signal word priority
        signal_words = [sw[0] for sw in entities.get('signal_word', [])]
        primary_signal = self._get_primary_signal_word(signal_words)

        return {
            'cas_numbers': valid_cas,
            'ec_numbers': [ec[0] for ec in entities.get('ec_number', [])],
            'hazard_statements': [h[0] for h in entities.get('hazard_statement', [])],
            'precautionary_statements': [p[0] for p in entities.get('precautionary_statement', [])],
            'signal_word': primary_signal,
            'pictograms': [pic[0] for pic in entities.get('pictogram', [])],
            'concentrations': self._extract_concentrations(entities),
            'physical_properties': self._extract_physical_properties(entities),
        }

    def _get_primary_signal_word(self, signal_words: List[str]) -> str:
        """Get the most severe signal word"""
        if 'DANGER' in [sw.upper() for sw in signal_words]:
            return 'DANGER'
        elif 'WARNING' in [sw.upper() for sw in signal_words]:
            return 'WARNING'
        elif 'CAUTION' in [sw.upper() for sw in signal_words]:
            return 'CAUTION'
        return ''

    def _extract_concentrations(self, entities: Dict) -> List[Dict]:
        """Extract concentration information"""
        concentrations = []
        
        # Range concentrations
        for conc_range in entities.get('concentration_range', []):
            concentrations.append({
                'type': 'range',
                'min_value': float(conc_range[0].split('-')[0]),
                'max_value': float(conc_range[0].split('-')[1]) if '-' in conc_range[0] else None,
                'unit': '%'
            })
        
        # Exact concentrations
        for conc_exact in entities.get('concentration_exact', []):
            concentrations.append({
                'type': 'exact',
                'value': float(conc_exact[0].replace('%', '')),
                'unit': '%'
            })
        
        return concentrations

    def _extract_physical_properties(self, entities: Dict) -> Dict[str, any]:
        """Extract physical and chemical properties"""
        properties = {}
        
        if entities.get('boiling_point'):
            properties['boiling_point'] = {
                'value': float(entities['boiling_point'][0][0]),
                'unit': '°C'
            }
        
        if entities.get('melting_point'):
            properties['melting_point'] = {
                'value': float(entities['melting_point'][0][0]),
                'unit': '°C'
            }
        
        if entities.get('flash_point'):
            properties['flash_point'] = {
                'value': float(entities['flash_point'][0][0]),
                'unit': '°C'
            }
        
        if entities.get('density'):
            properties['density'] = {
                'value': float(entities['density'][0][0]),
                'unit': 'g/cm³'
            }
        
        if entities.get('ph_value'):
            properties['ph'] = {
                'value': float(entities['ph_value'][0][0])
            }
        
        if entities.get('molecular_weight'):
            properties['molecular_weight'] = {
                'value': float(entities['molecular_weight'][0][0]),
                'unit': 'g/mol'
            }
        
        return properties

    def _load_hazard_statements(self):
        """Load H-statements dictionary"""
        return {
            'H200': 'Unstable explosive',
            'H201': 'Explosive; mass explosion hazard',
            'H202': 'Explosive; severe projection hazard',
            'H203': 'Explosive; fire, blast or projection hazard',
            'H204': 'Fire or projection hazard',
            'H205': 'May mass explode in fire',
            'H220': 'Extremely flammable gas',
            'H221': 'Flammable gas',
            'H222': 'Extremely flammable aerosol',
            'H223': 'Flammable aerosol',
            'H224': 'Extremely flammable liquid and vapour',
            'H225': 'Highly flammable liquid and vapour',
            'H226': 'Flammable liquid and vapour',
            'H227': 'Combustible liquid',
            'H228': 'Flammable solid',
            'H240': 'Heating may cause an explosion',
            'H241': 'Heating may cause a fire or explosion',
            'H242': 'Heating may cause a fire',
            'H250': 'Catches fire spontaneously if exposed to air',
            'H251': 'Self-heating; may catch fire',
            'H252': 'Self-heating in large quantities; may catch fire',
            'H260': 'In contact with water releases flammable gases which may ignite spontaneously',
            'H261': 'In contact with water releases flammable gas',
            'H270': 'May cause or intensify fire; oxidiser',
            'H271': 'May cause fire or explosion; strong oxidiser',
            'H272': 'May intensify fire; oxidiser',
            'H280': 'Contains gas under pressure; may explode if heated',
            'H281': 'Contains refrigerated gas; may cause cryogenic burns or injury',
            'H290': 'May be corrosive to metals',
            'H300': 'Fatal if swallowed',
            'H301': 'Toxic if swallowed',
            'H302': 'Harmful if swallowed',
            'H303': 'May be harmful if swallowed',
            'H304': 'May be fatal if swallowed and enters airways',
            'H305': 'May be harmful if swallowed and enters airways',
            'H310': 'Fatal in contact with skin',
            'H311': 'Toxic in contact with skin',
            'H312': 'Harmful in contact with skin',
            'H313': 'May be harmful in contact with skin',
            'H314': 'Causes severe skin burns and eye damage',
            'H315': 'Causes skin irritation',
            'H316': 'Causes mild skin irritation',
            'H317': 'May cause an allergic skin reaction',
            'H318': 'Causes serious eye damage',
            'H319': 'Causes serious eye irritation',
            'H320': 'Causes eye irritation',
            'H330': 'Fatal if inhaled',
            'H331': 'Toxic if inhaled',
            'H332': 'Harmful if inhaled',
            'H333': 'May be harmful if inhaled',
            'H334': 'May cause allergy or asthma symptoms or breathing difficulties if inhaled',
            'H335': 'May cause respiratory irritation',
            'H336': 'May cause drowsiness or dizziness',
            'H340': 'May cause genetic defects',
            'H341': 'Suspected of causing genetic defects',
            'H350': 'May cause cancer',
            'H351': 'Suspected of causing cancer',
            'H360': 'May damage fertility or the unborn child',
            'H361': 'Suspected of damaging fertility or the unborn child',
            'H362': 'May cause harm to breast-fed children',
            'H370': 'Causes damage to organs',
            'H371': 'May cause damage to organs',
            'H372': 'Causes damage to organs through prolonged or repeated exposure',
            'H373': 'May cause damage to organs through prolonged or repeated exposure',
            'H400': 'Very toxic to aquatic life',
            'H401': 'Toxic to aquatic life',
            'H402': 'Harmful to aquatic life',
            'H410': 'Very toxic to aquatic life with long lasting effects',
            'H411': 'Toxic to aquatic life with long lasting effects',
            'H412': 'Harmful to aquatic life with long lasting effects',
            'H413': 'May cause long lasting harmful effects to aquatic life',
            'H420': 'Harms public health and the environment by destroying ozone in the upper atmosphere',
        }

    def _load_pictogram_meanings(self):
        """Load GHS pictogram meanings"""
        return {
            'GHS01': 'Explosive',
            'GHS02': 'Flammable',
            'GHS03': 'Oxidizing',
            'GHS04': 'Compressed Gas',
            'GHS05': 'Corrosive',
            'GHS06': 'Toxic',
            'GHS07': 'Harmful',
            'GHS08': 'Health Hazard',
            'GHS09': 'Environmental Hazard'
        }

    def _load_chemical_synonyms(self):
        """Load common chemical name variations"""
        return {
            'sodium_bicarbonate': ['sodium hydrogen carbonate', 'baking soda', 'nahco3'],
            'hydrochloric_acid': ['muriatic acid', 'hcl'],
            'sulfuric_acid': ['sulphuric acid', 'h2so4'],
            'acetone': ['propanone', 'dimethyl ketone'],
            'ethanol': ['ethyl alcohol', 'grain alcohol'],
            'methanol': ['methyl alcohol', 'wood alcohol'],
            'isopropanol': ['isopropyl alcohol', 'ipa'],
            'sodium_hydroxide': ['caustic soda', 'naoh'],
            'calcium_carbonate': ['limestone', 'chalk', 'caco3'],
            'potassium_hydroxide': ['caustic potash', 'koh'],
        }
